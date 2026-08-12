from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from predictionlab.application.paper_validation import (
    CompletedPaperValidationCycle,
    PaperValidationRunFailedError,
    PaperValidationRunStatus,
    PaperValidationService,
    PortfolioReconciliation,
)
from predictionlab.domain.paper_trading import CurrencyUnit

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW

    def __call__(self) -> datetime:
        return self.now()


class MemoryRunStore:
    def __init__(self, *, consistent: bool = True) -> None:
        self.consistent = consistent
        self.started = []
        self.finished = []
        self.completed: CompletedPaperValidationCycle | None = None
        self.last_checked_at: datetime | None = None

    async def start(self, run) -> None:
        self.started.append(run)

    async def finish(self, result) -> None:
        self.finished.append(result)
        if result.status is PaperValidationRunStatus.COMPLETED:
            assert result.portfolio_id is not None
            assert result.reconciliation is not None
            assert result.result_hash is not None
            self.completed = CompletedPaperValidationCycle(
                run_id=result.run_id,
                portfolio_id=result.portfolio_id,
                prediction_count=result.prediction_count,
                decision_count=result.decision_count,
                trade_count=result.trade_count,
                settlement_count=result.settlement_count,
                reconciliation_result_hash=result.reconciliation.result_hash,
                result_hash=result.result_hash,
            )

    async def find_completed(self, cycle_key: str):
        return self.completed

    async def reconcile(
        self,
        portfolio_id: UUID,
        *,
        checked_at: datetime,
    ) -> PortfolioReconciliation:
        self.last_checked_at = checked_at
        discrepancies = () if self.consistent else ("ledger_cash_balance",)
        return PortfolioReconciliation(
            portfolio_id=portfolio_id,
            checked_at=checked_at,
            is_consistent=self.consistent,
            discrepancy_codes=discrepancies,
            expected_cash_balance=Decimal("100"),
            actual_cash_balance=(
                Decimal("100") if self.consistent else Decimal("99")
            ),
            expected_reserved_balance=Decimal("0"),
            actual_reserved_balance=Decimal("0"),
            expected_realized_pnl=Decimal("0"),
            actual_realized_pnl=Decimal("0"),
            expected_unrealized_pnl=Decimal("0"),
            actual_unrealized_pnl=Decimal("0"),
            expected_equity=Decimal("100"),
            actual_equity=(
                Decimal("100") if self.consistent else Decimal("99")
            ),
            expected_total_exposure=Decimal("0"),
            actual_total_exposure=Decimal("0"),
            initial_ledger_entries=1,
            result_hash="a" * 64,
        )


class StaticLock:
    def __init__(self, acquired: bool = True) -> None:
        self.acquired = acquired

    @asynccontextmanager
    async def acquire(self):
        yield self.acquired


class PredictionRunner:
    def __init__(self) -> None:
        self.calls = 0
        self.prediction_id = uuid4()
        self.last_kwargs = {}

    async def run_batch(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return (
            SimpleNamespace(
                prediction_run_id=self.prediction_id,
                result_hash="d" * 64,
            ),
        )


class PaperRunner:
    configuration_hash = "b" * 64

    def __init__(self) -> None:
        self.portfolio_id = uuid4()
        self.portfolio_calls = 0
        self.batch_calls = 0
        self.settlement_calls = 0
        self.last_settlement_command = None

    async def create_portfolio(self, command):
        self.portfolio_calls += 1
        return SimpleNamespace(
            portfolio=SimpleNamespace(portfolio_id=self.portfolio_id),
            created=self.portfolio_calls == 1,
        )

    async def run_batch(self, **kwargs):
        self.batch_calls += 1
        return (
            SimpleNamespace(
                trade=SimpleNamespace(),
                artifact_hashes=("e" * 64,),
            ),
        )

    async def settle(self, command):
        self.settlement_calls += 1
        self.last_settlement_command = command
        return SimpleNamespace(
            settlements=(),
            artifact_hashes=("f" * 64,),
        )


def service(
    store: MemoryRunStore,
    *,
    lock: StaticLock | None = None,
    clock=None,
) -> tuple[PaperValidationService, PredictionRunner, PaperRunner]:
    predictions = PredictionRunner()
    paper = PaperRunner()
    return (
        PaperValidationService(
            prediction_runner=predictions,
            paper_runner=paper,
            run_store=store,
            validation_lock=lock or StaticLock(),
            validation_configuration_hash="c" * 64,
            portfolio_name="Continuous validation",
            currency_unit=CurrencyUnit.USD_SIMULATED,
            initial_balance=Decimal("100"),
            random_seed=17,
            provider_codes=("manifold",),
            only_with_new_observations=True,
            clock=clock or FixedClock(),
        ),
        predictions,
        paper,
    )


@pytest.mark.asyncio
async def test_cycle_runs_full_flow_and_skips_completed_duplicate() -> None:
    store = MemoryRunStore()
    runner, predictions, paper = service(store)

    first = await runner.run_cycle(scheduled_for=NOW)
    second = await runner.run_cycle(scheduled_for=NOW)

    assert first.status is PaperValidationRunStatus.COMPLETED
    assert first.prediction_count == 1
    assert first.decision_count == 1
    assert first.trade_count == 1
    assert first.reconciliation is not None
    assert first.reconciliation.is_consistent
    assert second.status is PaperValidationRunStatus.SKIPPED_COMPLETED
    assert first.cycle_key == second.cycle_key
    assert predictions.calls == 1
    assert predictions.last_kwargs["provider_codes"] == ("manifold",)
    assert predictions.last_kwargs["only_with_new_observations"] is True
    assert paper.batch_calls == 1
    assert len(store.started) == 2
    assert len(store.finished) == 2


@pytest.mark.asyncio
async def test_cycle_records_lock_contention_without_side_effects() -> None:
    store = MemoryRunStore()
    runner, predictions, paper = service(store, lock=StaticLock(False))

    result = await runner.run_cycle(scheduled_for=NOW)

    assert result.status is PaperValidationRunStatus.SKIPPED_LOCKED
    assert predictions.calls == 0
    assert paper.portfolio_calls == 0
    assert store.finished[0].status is PaperValidationRunStatus.SKIPPED_LOCKED


@pytest.mark.asyncio
async def test_first_cycle_uses_execution_time_for_portfolio_mutations() -> None:
    execution_time = datetime(2026, 7, 28, 12, 0, 1, tzinfo=UTC)
    store = MemoryRunStore()
    runner, _, paper = service(
        store,
        clock=SimpleNamespace(now=lambda: execution_time),
    )

    await runner.run_cycle(scheduled_for=NOW)

    assert paper.last_settlement_command.settled_at == execution_time
    assert store.last_checked_at == execution_time


@pytest.mark.asyncio
async def test_reconciliation_mismatch_fails_cycle_with_safe_error() -> None:
    store = MemoryRunStore(consistent=False)
    runner, _, _ = service(store)

    with pytest.raises(PaperValidationRunFailedError) as raised:
        await runner.run_cycle(scheduled_for=NOW)

    assert raised.value.result.status is PaperValidationRunStatus.FAILED
    assert (
        raised.value.result.safe_error_type
        == "PaperAccountingReconciliationError"
    )
    assert raised.value.result.reconciliation is not None
    assert raised.value.result.reconciliation.discrepancy_codes == (
        "ledger_cash_balance",
    )
    assert store.finished[0] == raised.value.result
