"""Composition root for continuous paper validation."""

from __future__ import annotations

from dataclasses import dataclass

from predictionlab.application.paper_validation import (
    PaperValidationService,
    validation_configuration_hash,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.settings import Settings
from predictionlab.domain.paper_trading import CurrencyUnit
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


def create_paper_validation_runtime(
    settings: Settings,
    *,
    clock: Clock | None = None,
) -> PaperValidationRuntime:
    resolved_clock = clock or SystemClock()
    resources = create_resources(settings)
    prediction_orchestrator = create_prediction_orchestrator(
        session_factory=resources.session_factory,
        settings=settings,
        clock=resolved_clock,
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
            "only_new_observations": (
                settings.paper_validation_only_new_observations
            ),
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
        only_with_new_observations=(
            settings.paper_validation_only_new_observations
        ),
        clock=resolved_clock,
    )
    return PaperValidationRuntime(
        resources=resources,
        worker=PaperValidationWorker(
            runner=service,
            interval_seconds=settings.paper_validation_interval_seconds,
            run_immediately=settings.paper_validation_run_immediately,
            clock=resolved_clock,
        ),
    )
