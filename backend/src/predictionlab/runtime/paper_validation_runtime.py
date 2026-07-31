"""Composition root for continuous paper validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from predictionlab.application.paper_validation import (
    PaperValidationService,
    validation_configuration_hash,
)
from predictionlab.application.paper_validation.models import (
    PaperValidationRunResult,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.settings import Settings
from predictionlab.domain.agents import JsonScalar
from predictionlab.domain.paper_trading import CurrencyUnit
from predictionlab.domain.predictions import PredictionRun
from predictionlab.infrastructure.database.paper_validation import (
    PostgresPaperValidationLock,
    SqlAlchemyPaperValidationRunStore,
)
from predictionlab.infrastructure.resources import (
    InfrastructureResources,
    create_resources,
)
from predictionlab.runtime.paper_trading import create_paper_trading_orchestrator
from predictionlab.runtime.paper_validation_worker import PaperValidationWorker
from predictionlab.runtime.predictions import create_prediction_orchestrator


@dataclass(slots=True)
class PaperValidationRuntime:
    resources: InfrastructureResources
    worker: PaperValidationWorker

    async def close(self) -> None:
        await self.resources.close()


class _CachingPredictionBatchRunner:
    """Share one immutable prediction batch across parallel paper campaigns."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate
        self._key: tuple[object, ...] | None = None
        self._result: tuple[PredictionRun, ...] = ()

    async def run_batch(
        self,
        *,
        predicted_at: datetime,
        experiment_run_id: UUID | None,
        random_seed: int,
        provider_codes: tuple[str, ...] = (),
        only_with_new_observations: bool = False,
        context: dict[str, JsonScalar] | None = None,
        model_configuration: dict[str, JsonScalar] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> tuple[PredictionRun, ...]:
        key = (
            predicted_at,
            experiment_run_id,
            random_seed,
            provider_codes,
            only_with_new_observations,
            tuple(sorted((context or {}).items())),
            tuple(sorted((model_configuration or {}).items())),
        )
        if key != self._key:
            self._result = await self._delegate.run_batch(
                predicted_at=predicted_at,
                experiment_run_id=experiment_run_id,
                random_seed=random_seed,
                provider_codes=provider_codes,
                only_with_new_observations=only_with_new_observations,
                context=context,
                model_configuration=model_configuration,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            self._key = key
        return self._result


class _ParallelCampaignRunner:
    def __init__(
        self,
        primary: PaperValidationService,
        additional: tuple[PaperValidationService, ...],
    ) -> None:
        self._primary = primary
        self._additional = additional

    async def run_cycle(
        self,
        *,
        scheduled_for: datetime,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> PaperValidationRunResult:
        primary_result: PaperValidationRunResult | None = None
        errors: list[Exception] = []
        services = (self._primary, *self._additional)
        for index, service in enumerate(services):
            try:
                result = await service.run_cycle(
                    scheduled_for=scheduled_for,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                )
                if index == 0:
                    primary_result = result
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise errors[0]
        if primary_result is None:
            raise RuntimeError("primary paper campaign produced no result")
        return primary_result


def create_paper_validation_runtime(
    settings: Settings,
    *,
    clock: Clock | None = None,
) -> PaperValidationRuntime:
    resolved_clock = clock or SystemClock()
    resources = create_resources(settings)
    prediction_orchestrator = _CachingPredictionBatchRunner(
        create_prediction_orchestrator(
            session_factory=resources.session_factory,
            settings=settings,
            clock=resolved_clock,
        )
    )
    paper_orchestrator = create_paper_trading_orchestrator(
        session_factory=resources.session_factory,
        settings=settings,
        clock=resolved_clock,
    )
    configuration_hash = validation_configuration_hash(
        prediction_configuration={
            "minimum_confidence": settings.prediction_minimum_confidence,
            "maximum_disagreement": settings.prediction_maximum_disagreement,
            "maximum_observation_age_seconds": (
                settings.prediction_maximum_observation_age_seconds
            ),
            "weak_edge": settings.prediction_weak_edge,
            "moderate_edge": settings.prediction_moderate_edge,
            "strong_edge": settings.prediction_strong_edge,
        },
        paper_configuration_hash=paper_orchestrator.configuration_hash,
        random_seed=settings.paper_validation_random_seed,
        runtime_configuration={
            "code_version": settings.code_version or "unversioned",
            "currency_unit": settings.paper_currency_unit,
            "initial_balance": settings.paper_initial_balance,
            "portfolio_name": settings.paper_validation_portfolio_name,
            "interval_seconds": settings.paper_validation_interval_seconds,
            "provider_codes": settings.paper_validation_provider_codes,
            "only_new_observations": (settings.paper_validation_only_new_observations),
        },
    )
    service = PaperValidationService(
        prediction_runner=prediction_orchestrator,
        paper_runner=paper_orchestrator,
        run_store=SqlAlchemyPaperValidationRunStore(resources.session_factory),
        validation_lock=PostgresPaperValidationLock(resources.database_engine),
        validation_configuration_hash=configuration_hash,
        portfolio_name=settings.paper_validation_portfolio_name,
        currency_unit=CurrencyUnit(settings.paper_currency_unit),
        initial_balance=settings.paper_initial_balance,
        random_seed=settings.paper_validation_random_seed,
        provider_codes=settings.paper_validation_provider_codes,
        only_with_new_observations=(settings.paper_validation_only_new_observations),
        clock=resolved_clock,
    )
    additional_services: list[PaperValidationService] = []
    if settings.experimental_campaign_enabled:
        experimental_orchestrator = create_paper_trading_orchestrator(
            session_factory=resources.session_factory,
            settings=settings,
            clock=resolved_clock,
            campaign_id="experimental-v1",
            minimum_entry_edge=Decimal("0"),
            minimum_net_edge=settings.experimental_min_net_edge,
        )
        experimental_hash = validation_configuration_hash(
            prediction_configuration={
                "minimum_confidence": settings.prediction_minimum_confidence,
                "maximum_disagreement": settings.prediction_maximum_disagreement,
                "maximum_observation_age_seconds": (
                    settings.prediction_maximum_observation_age_seconds
                ),
                "consensus_version": "2.0.0",
            },
            paper_configuration_hash=(experimental_orchestrator.configuration_hash),
            random_seed=settings.paper_validation_random_seed,
            runtime_configuration={
                "campaign_id": "experimental-v1",
                "minimum_net_edge": settings.experimental_min_net_edge,
                "code_version": settings.code_version or "unversioned",
                "currency_unit": settings.paper_currency_unit,
                "initial_balance": settings.paper_initial_balance,
                "portfolio_name": "Experimental paper validation",
                "interval_seconds": (settings.paper_validation_interval_seconds),
                "provider_codes": settings.paper_validation_provider_codes,
                "only_new_observations": (settings.paper_validation_only_new_observations),
            },
        )
        additional_services.append(
            PaperValidationService(
                prediction_runner=prediction_orchestrator,
                paper_runner=experimental_orchestrator,
                run_store=SqlAlchemyPaperValidationRunStore(resources.session_factory),
                validation_lock=PostgresPaperValidationLock(resources.database_engine),
                validation_configuration_hash=experimental_hash,
                portfolio_name="Experimental paper validation",
                currency_unit=CurrencyUnit(settings.paper_currency_unit),
                initial_balance=settings.paper_initial_balance,
                random_seed=settings.paper_validation_random_seed,
                provider_codes=settings.paper_validation_provider_codes,
                only_with_new_observations=(settings.paper_validation_only_new_observations),
                clock=resolved_clock,
            )
        )
    return PaperValidationRuntime(
        resources=resources,
        worker=PaperValidationWorker(
            runner=_ParallelCampaignRunner(
                service,
                tuple(additional_services),
            ),
            interval_seconds=settings.paper_validation_interval_seconds,
            run_immediately=settings.paper_validation_run_immediately,
            clock=resolved_clock,
        ),
    )
