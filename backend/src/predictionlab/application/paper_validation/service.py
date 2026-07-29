"""Idempotent end-to-end cycle for continuous simulated validation."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter
from typing import Protocol
from uuid import UUID, uuid4

from predictionlab.application.paper_trading import (
    CreatePaperPortfolio,
    CreatePaperPortfolioResult,
    PaperTradingOutcome,
    SettlementBatchResult,
    SettlePaperPortfolio,
)
from predictionlab.application.paper_validation.models import (
    CompletedPaperValidationCycle,
    PaperValidationRunResult,
    PaperValidationRunStarted,
    PaperValidationRunStatus,
    PortfolioReconciliation,
)
from predictionlab.application.paper_validation.repository import (
    PaperValidationLock,
    PaperValidationRunStore,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.agents import JsonScalar
from predictionlab.domain.paper_trading import CurrencyUnit
from predictionlab.domain.predictions import PredictionRun

logger = logging.getLogger(__name__)


class PredictionBatchRunner(Protocol):
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
    ) -> tuple[PredictionRun, ...]: ...


class PaperTradingBatchRunner(Protocol):
    configuration_hash: str

    async def create_portfolio(
        self,
        command: CreatePaperPortfolio,
    ) -> CreatePaperPortfolioResult: ...

    async def run_batch(
        self,
        *,
        portfolio_id: UUID,
        prediction_run_ids: Sequence[UUID],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> tuple[PaperTradingOutcome, ...]: ...

    async def settle(
        self,
        command: SettlePaperPortfolio,
    ) -> SettlementBatchResult: ...


class PaperValidationRunFailedError(RuntimeError):
    def __init__(self, result: PaperValidationRunResult) -> None:
        super().__init__(result.safe_error_type or "paper validation cycle failed")
        self.result = result


class PaperValidationService:
    """Run prediction, simulated execution, settlement and accounting checks."""

    def __init__(
        self,
        *,
        prediction_runner: PredictionBatchRunner,
        paper_runner: PaperTradingBatchRunner,
        run_store: PaperValidationRunStore,
        validation_lock: PaperValidationLock,
        validation_configuration_hash: str,
        portfolio_name: str,
        currency_unit: CurrencyUnit,
        initial_balance: Decimal,
        random_seed: int,
        provider_codes: tuple[str, ...] = (),
        only_with_new_observations: bool = False,
        clock: Clock | None = None,
    ) -> None:
        if not validation_configuration_hash:
            raise ValueError("validation_configuration_hash cannot be blank")
        if not portfolio_name.strip():
            raise ValueError("portfolio_name cannot be blank")
        self._predictions = prediction_runner
        self._paper = paper_runner
        self._store = run_store
        self._lock = validation_lock
        self._validation_configuration_hash = validation_configuration_hash
        self._portfolio_name = (
            f"{portfolio_name.strip()} [{validation_configuration_hash[:8]}]"
        )
        self._currency_unit = currency_unit
        self._initial_balance = initial_balance
        self._random_seed = random_seed
        self._provider_codes = provider_codes
        self._only_with_new_observations = only_with_new_observations
        self._clock = clock or SystemClock()

    async def run_cycle(
        self,
        *,
        scheduled_for: datetime,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> PaperValidationRunResult:
        scheduled_for = _require_utc(scheduled_for)
        started_at = self._clock.now()
        started_perf = perf_counter()
        run_id = uuid4()
        resolved_correlation_id = correlation_id or str(uuid4())
        cycle_key = canonical_sha256(
            {
                "runtime": "continuous_paper_validation_v1",
                "scheduled_for": scheduled_for,
                "configuration_hash": self._validation_configuration_hash,
            }
        )
        await self._store.start(
            PaperValidationRunStarted(
                run_id=run_id,
                cycle_key=cycle_key,
                scheduled_for=scheduled_for,
                started_at=started_at,
                correlation_id=resolved_correlation_id,
                causation_id=causation_id,
            )
        )
        logger.info(
            "paper_validation_cycle_started",
            extra={
                "run_id": str(run_id),
                "cycle_key": cycle_key,
                "scheduled_for": scheduled_for.isoformat(),
                "configuration_hash": self._validation_configuration_hash,
                "correlation_id": resolved_correlation_id,
                "causation_id": causation_id,
                "simulation_only": True,
            },
        )
        try:
            async with self._lock.acquire() as acquired:
                if not acquired:
                    return await self._finish_skipped(
                        run_id=run_id,
                        cycle_key=cycle_key,
                        scheduled_for=scheduled_for,
                        started_at=started_at,
                        started_perf=started_perf,
                        correlation_id=resolved_correlation_id,
                        causation_id=causation_id,
                        status=PaperValidationRunStatus.SKIPPED_LOCKED,
                    )
                completed = await self._store.find_completed(cycle_key)
                if completed is not None:
                    return await self._finish_completed_duplicate(
                        run_id=run_id,
                        cycle_key=cycle_key,
                        scheduled_for=scheduled_for,
                        started_at=started_at,
                        started_perf=started_perf,
                        correlation_id=resolved_correlation_id,
                        causation_id=causation_id,
                        completed=completed,
                    )
                result = await self._execute(
                    run_id=run_id,
                    cycle_key=cycle_key,
                    scheduled_for=scheduled_for,
                    started_at=started_at,
                    started_perf=started_perf,
                    correlation_id=resolved_correlation_id,
                    causation_id=causation_id,
                )
        except Exception as exc:
            if isinstance(exc, PaperValidationRunFailedError):
                raise
            result = self._result(
                run_id=run_id,
                cycle_key=cycle_key,
                scheduled_for=scheduled_for,
                started_at=started_at,
                started_perf=started_perf,
                status=PaperValidationRunStatus.FAILED,
                correlation_id=resolved_correlation_id,
                causation_id=causation_id,
                safe_error_type=type(exc).__name__,
            )
            await self._store.finish(result)
            logger.exception(
                "paper_validation_cycle_failed",
                extra={
                    "run_id": str(run_id),
                    "cycle_key": cycle_key,
                    "safe_error_type": type(exc).__name__,
                    "correlation_id": resolved_correlation_id,
                    "causation_id": causation_id,
                    "simulation_only": True,
                },
            )
            raise PaperValidationRunFailedError(result) from exc
        await self._store.finish(result)
        self._log_finished(result)
        if result.status is PaperValidationRunStatus.FAILED:
            raise PaperValidationRunFailedError(result)
        return result

    async def _execute(
        self,
        *,
        run_id: UUID,
        cycle_key: str,
        scheduled_for: datetime,
        started_at: datetime,
        started_perf: float,
        correlation_id: str,
        causation_id: str | None,
    ) -> PaperValidationRunResult:
        cycle_causation = causation_id or f"paper-validation:{cycle_key}"
        portfolio_result = await self._paper.create_portfolio(
            CreatePaperPortfolio(
                name=self._portfolio_name,
                currency_unit=self._currency_unit,
                initial_balance=self._initial_balance,
                correlation_id=correlation_id,
                causation_id=cycle_causation,
            )
        )
        portfolio_id = portfolio_result.portfolio.portfolio_id
        predictions = await self._predictions.run_batch(
            predicted_at=scheduled_for,
            experiment_run_id=None,
            random_seed=self._random_seed,
            provider_codes=self._provider_codes,
            only_with_new_observations=self._only_with_new_observations,
            correlation_id=correlation_id,
            causation_id=cycle_causation,
        )
        outcomes = await self._paper.run_batch(
            portfolio_id=portfolio_id,
            prediction_run_ids=tuple(item.prediction_run_id for item in predictions),
            correlation_id=correlation_id,
            causation_id=cycle_causation,
        )
        settlements = await self._paper.settle(
            SettlePaperPortfolio(
                portfolio_id=portfolio_id,
                settled_at=scheduled_for,
                correlation_id=correlation_id,
                causation_id=cycle_causation,
            )
        )
        reconciliation = await self._store.reconcile(
            portfolio_id,
            checked_at=scheduled_for,
        )
        status = (
            PaperValidationRunStatus.COMPLETED
            if reconciliation.is_consistent
            else PaperValidationRunStatus.FAILED
        )
        safe_error_type = (
            None if reconciliation.is_consistent else "PaperAccountingReconciliationError"
        )
        counts = {
            "prediction_count": len(predictions),
            "decision_count": len(outcomes),
            "trade_count": sum(item.trade is not None for item in outcomes),
            "settlement_count": len(settlements.settlements),
        }
        result_hash = canonical_sha256(
            {
                "cycle_key": cycle_key,
                "portfolio_id": portfolio_id,
                **counts,
                "prediction_result_hashes": tuple(
                    item.result_hash for item in predictions
                ),
                "paper_artifact_hashes": tuple(
                    artifact_hash
                    for outcome in outcomes
                    for artifact_hash in outcome.artifact_hashes
                ),
                "settlement_artifact_hashes": settlements.artifact_hashes,
                "reconciliation_result_hash": reconciliation.result_hash,
                "paper_configuration_hash": self._paper.configuration_hash,
            }
        )
        return self._result(
            run_id=run_id,
            cycle_key=cycle_key,
            scheduled_for=scheduled_for,
            started_at=started_at,
            started_perf=started_perf,
            status=status,
            correlation_id=correlation_id,
            causation_id=causation_id,
            portfolio_id=portfolio_id,
            reconciliation=reconciliation,
            safe_error_type=safe_error_type,
            result_hash=result_hash,
            **counts,
        )

    async def _finish_skipped(
        self,
        *,
        run_id: UUID,
        cycle_key: str,
        scheduled_for: datetime,
        started_at: datetime,
        started_perf: float,
        correlation_id: str,
        causation_id: str | None,
        status: PaperValidationRunStatus,
    ) -> PaperValidationRunResult:
        result = self._result(
            run_id=run_id,
            cycle_key=cycle_key,
            scheduled_for=scheduled_for,
            started_at=started_at,
            started_perf=started_perf,
            status=status,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        await self._store.finish(result)
        self._log_finished(result)
        return result

    async def _finish_completed_duplicate(
        self,
        *,
        run_id: UUID,
        cycle_key: str,
        scheduled_for: datetime,
        started_at: datetime,
        started_perf: float,
        correlation_id: str,
        causation_id: str | None,
        completed: CompletedPaperValidationCycle,
    ) -> PaperValidationRunResult:
        result = self._result(
            run_id=run_id,
            cycle_key=cycle_key,
            scheduled_for=scheduled_for,
            started_at=started_at,
            started_perf=started_perf,
            status=PaperValidationRunStatus.SKIPPED_COMPLETED,
            correlation_id=correlation_id,
            causation_id=causation_id,
            portfolio_id=completed.portfolio_id,
            prediction_count=completed.prediction_count,
            decision_count=completed.decision_count,
            trade_count=completed.trade_count,
            settlement_count=completed.settlement_count,
            result_hash=completed.result_hash,
        )
        await self._store.finish(result)
        self._log_finished(result)
        return result

    def _result(
        self,
        *,
        run_id: UUID,
        cycle_key: str,
        scheduled_for: datetime,
        started_at: datetime,
        started_perf: float,
        status: PaperValidationRunStatus,
        correlation_id: str,
        causation_id: str | None,
        portfolio_id: UUID | None = None,
        prediction_count: int = 0,
        decision_count: int = 0,
        trade_count: int = 0,
        settlement_count: int = 0,
        reconciliation: PortfolioReconciliation | None = None,
        safe_error_type: str | None = None,
        result_hash: str | None = None,
    ) -> PaperValidationRunResult:
        return PaperValidationRunResult(
            run_id=run_id,
            cycle_key=cycle_key,
            scheduled_for=scheduled_for,
            started_at=started_at,
            finished_at=self._clock.now(),
            duration_ms=Decimal(str(round((perf_counter() - started_perf) * 1_000, 3))),
            status=status,
            correlation_id=correlation_id,
            causation_id=causation_id,
            portfolio_id=portfolio_id,
            prediction_count=prediction_count,
            decision_count=decision_count,
            trade_count=trade_count,
            settlement_count=settlement_count,
            reconciliation=reconciliation,
            safe_error_type=safe_error_type,
            result_hash=result_hash,
        )

    @staticmethod
    def _log_finished(result: PaperValidationRunResult) -> None:
        logger.info(
            "paper_validation_cycle_finished",
            extra={
                "run_id": str(result.run_id),
                "cycle_key": result.cycle_key,
                "status": result.status.value,
                "portfolio_id": (
                    str(result.portfolio_id) if result.portfolio_id is not None else None
                ),
                "prediction_count": result.prediction_count,
                "decision_count": result.decision_count,
                "trade_count": result.trade_count,
                "settlement_count": result.settlement_count,
                "reconciliation_ok": (
                    result.reconciliation.is_consistent
                    if result.reconciliation is not None
                    else None
                ),
                "safe_error_type": result.safe_error_type,
                "duration_ms": str(result.duration_ms),
                "correlation_id": result.correlation_id,
                "causation_id": result.causation_id,
                "simulation_only": True,
            },
        )


def validation_configuration_hash(
    *,
    prediction_configuration: Mapping[str, object],
    paper_configuration_hash: str,
    random_seed: int,
    runtime_configuration: Mapping[str, object],
) -> str:
    return canonical_sha256(
        {
            "runtime": "continuous_paper_validation_v1",
            "prediction_configuration": prediction_configuration,
            "paper_configuration_hash": paper_configuration_hash,
            "random_seed": random_seed,
            "runtime_configuration": runtime_configuration,
        }
    )


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scheduled_for must be timezone-aware")
    return value.astimezone(UTC)
