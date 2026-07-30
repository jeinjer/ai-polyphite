from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from predictionlab.application.paper_trading import (
    ManualPaperTradeStatus,
    PaperTradingIdempotencyConflictError,
    PaperTradingOrchestrator,
    PaperTradingOutcome,
    PortfolioExposure,
    RunManualPaperTrade,
    TradingPredictionContext,
)
from predictionlab.domain.markets import MarketStatus
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolio,
    PaperPortfolioStatus,
    PositionSide,
    TradeDecisionSource,
)
from predictionlab.domain.predictions import (
    OpportunityLevel,
    PredictionRunStatus,
)

NOW = datetime(2026, 7, 30, 12, tzinfo=UTC)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000001301")
PREDICTION_ID = UUID("00000000-0000-4000-8000-000000001302")
MARKET_ID = UUID("00000000-0000-4000-8000-000000001303")


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryPaperRepository:
    def __init__(self, *, paused: bool = False) -> None:
        self.portfolio = PaperPortfolio(
            portfolio_id=PORTFOLIO_ID,
            name="Manual overrides",
            currency_unit=CurrencyUnit.MANA_SIMULATED,
            initial_balance=Decimal("100"),
            cash_balance=Decimal("100"),
            reserved_balance=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            equity=Decimal("100"),
            total_exposure=Decimal("0"),
            status=(
                PaperPortfolioStatus.PAUSED
                if paused
                else PaperPortfolioStatus.ACTIVE
            ),
            strategy_configuration_hash="a" * 64,
            experiment_run_id=None,
            created_at=NOW,
            updated_at=NOW,
        )
        self.context = TradingPredictionContext(
            prediction_run_id=PREDICTION_ID,
            prediction_result_hash="b" * 64,
            experiment_run_id=None,
            market_id=MARKET_ID,
            market_title="Manual override test",
            category="testing",
            predicted_at=NOW - timedelta(hours=1),
            prediction_status=PredictionRunStatus.ABSTAINED,
            market_probability=Decimal("0.60"),
            system_probability=None,
            edge=None,
            confidence=Decimal("0.10"),
            opportunity_level=OpportunityLevel.NONE,
            disagreement_score=Decimal("0.90"),
            market_status_as_of=MarketStatus.OPEN,
            observation_at=NOW - timedelta(minutes=5),
            liquidity=Decimal("100"),
        )
        self.decision = None
        self.order = None
        self.trade = None
        self.position = None

    async def find_outcome_by_idempotency(self, **kwargs):
        del kwargs
        return self._outcome()

    async def find_outcome(self, **kwargs):
        del kwargs
        return self._outcome()

    async def get_portfolio(self, portfolio_id, *, for_update=False):
        del for_update
        return self.portfolio if portfolio_id == PORTFOLIO_ID else None

    async def prediction_context(self, prediction_run_id, *, as_of=None):
        assert prediction_run_id == PREDICTION_ID
        assert as_of == NOW
        return self.context

    async def exposure(self, **kwargs):
        del kwargs
        return PortfolioExposure(
            total=Decimal("0"),
            market=Decimal("0"),
            category=Decimal("0"),
        )

    async def add_decision(self, decision):
        self.decision = decision

    async def add_order(self, order):
        self.order = order

    async def add_trade(self, trade):
        self.trade = trade

    async def add_position(self, position):
        self.position = position

    async def update_portfolio(self, portfolio):
        self.portfolio = portfolio

    async def add_ledger_entry(self, entry):
        del entry

    def _outcome(self) -> PaperTradingOutcome | None:
        if self.decision is None:
            return None
        return PaperTradingOutcome(
            self.decision,
            self.order,
            self.trade,
            self.position,
        )


class MemoryUnitOfWork:
    def __init__(self, repository: MemoryPaperRepository) -> None:
        self.paper_trading = repository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        del exc_type, exc, traceback

    async def commit(self):
        return None

    async def rollback(self):
        return None


def orchestrator(repository: MemoryPaperRepository) -> PaperTradingOrchestrator:
    service = PaperTradingOrchestrator(
        unit_of_work=lambda: MemoryUnitOfWork(repository),
        clock=FixedClock(),
    )
    repository.portfolio = replace(
        repository.portfolio,
        strategy_configuration_hash=service.configuration_hash,
    )
    return service


def command() -> RunManualPaperTrade:
    return RunManualPaperTrade(
        portfolio_id=PORTFOLIO_ID,
        prediction_run_id=PREDICTION_ID,
        side=PositionSide.NO,
        requested_stake=Decimal("1"),
        override_reason="Quiero probar el lado contrario.",
        idempotency_key="manual-override-1",
    )


@pytest.mark.asyncio
async def test_manual_override_ignores_agent_abstention_but_keeps_risk() -> None:
    repository = MemoryPaperRepository()
    service = orchestrator(repository)

    first = await service.run_manual_override(command())
    duplicate = await service.run_manual_override(command())

    assert first.status is ManualPaperTradeStatus.FILLED
    assert first.outcome.trade is not None
    assert first.outcome.trade.side is PositionSide.NO
    assert (
        first.outcome.decision.decision_source
        is TradeDecisionSource.MANUAL_OVERRIDE
    )
    assert first.outcome.decision.override_reason is not None
    assert duplicate.status is ManualPaperTradeStatus.DUPLICATE
    assert (
        duplicate.outcome.decision.decision_id
        == first.outcome.decision.decision_id
    )


@pytest.mark.asyncio
async def test_manual_override_rejects_paused_portfolio() -> None:
    repository = MemoryPaperRepository(paused=True)
    result = await orchestrator(repository).run_manual_override(command())

    assert result.status is ManualPaperTradeStatus.REJECTED
    assert result.outcome.trade is None
    assert "portfolio_inactive" in result.outcome.decision.rejection_reasons
    assert result.outcome.decision.side is PositionSide.NO


@pytest.mark.asyncio
async def test_manual_override_rejects_reused_key_with_different_input() -> None:
    repository = MemoryPaperRepository()
    service = orchestrator(repository)
    await service.run_manual_override(command())

    with pytest.raises(
        PaperTradingIdempotencyConflictError,
        match="different input",
    ):
        await service.run_manual_override(
            replace(
                command(),
                side=PositionSide.YES,
            )
        )
