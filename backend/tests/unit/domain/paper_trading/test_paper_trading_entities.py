from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolio,
    PaperPortfolioStatus,
    PaperTradingInvariantError,
    PositionSide,
    TradeDecision,
    TradeDecisionSource,
    TradeDecisionType,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000901")


def portfolio() -> PaperPortfolio:
    return PaperPortfolio(
        portfolio_id=PORTFOLIO_ID,
        name="Deterministic test",
        currency_unit=CurrencyUnit.USD_SIMULATED,
        initial_balance=Decimal("100"),
        cash_balance=Decimal("100"),
        reserved_balance=Decimal("0"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        equity=Decimal("100"),
        total_exposure=Decimal("0"),
        status=PaperPortfolioStatus.ACTIVE,
        strategy_configuration_hash="a" * 64,
        experiment_run_id=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_portfolio_accounting_is_immutable_and_reconciles() -> None:
    initial = portfolio()

    opened = initial.open_position(
        net_cost=Decimal("2"),
        initial_mark_value=Decimal("1.90"),
        occurred_at=NOW + timedelta(minutes=1),
    )
    marked = opened.update_mark(
        previous_unrealized_pnl=Decimal("-0.10"),
        current_unrealized_pnl=Decimal("0.50"),
        occurred_at=NOW + timedelta(minutes=2),
    )
    settled = marked.settle_position(
        invested_amount=Decimal("2"),
        previous_unrealized_pnl=Decimal("0.50"),
        net_payout=Decimal("3"),
        realized_pnl=Decimal("1"),
        occurred_at=NOW + timedelta(minutes=3),
    )

    assert initial.cash_balance == Decimal("100")
    assert opened.equity == Decimal("99.90")
    assert marked.equity == Decimal("100.50")
    assert settled.cash_balance == Decimal("101")
    assert settled.reserved_balance == Decimal("0")
    assert settled.realized_pnl == Decimal("1")
    assert settled.equity == Decimal("101")


def test_portfolio_rejects_leverage_and_inconsistent_equity() -> None:
    with pytest.raises(PaperTradingInvariantError, match="insufficient cash"):
        portfolio().open_position(
            net_cost=Decimal("101"),
            initial_mark_value=Decimal("101"),
            occurred_at=NOW,
        )
    with pytest.raises(PaperTradingInvariantError, match="equity must equal"):
        PaperPortfolio(
            portfolio_id=PORTFOLIO_ID,
            name="Broken",
            currency_unit=CurrencyUnit.MANA_SIMULATED,
            initial_balance=Decimal("100"),
            cash_balance=Decimal("100"),
            reserved_balance=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            equity=Decimal("99"),
            total_exposure=Decimal("0"),
            status=PaperPortfolioStatus.ACTIVE,
            strategy_configuration_hash="b" * 64,
            experiment_run_id=None,
            created_at=NOW,
            updated_at=NOW,
        )


def test_manual_decision_requires_explicit_override_provenance() -> None:
    decision = TradeDecision(
        decision_id=UUID("00000000-0000-4000-8000-000000000911"),
        prediction_run_id=UUID("00000000-0000-4000-8000-000000000912"),
        portfolio_id=PORTFOLIO_ID,
        decided_at=NOW,
        decision=TradeDecisionType.BUY_YES,
        market_probability=Decimal("0.60"),
        system_probability=Decimal("0.55"),
        edge=Decimal("-0.05"),
        confidence=Decimal("0.20"),
        opportunity_level="none",
        proposed_stake=Decimal("1"),
        approved_stake=Decimal("1"),
        rejection_reasons=(),
        risk_checks=("manual_override:confirmed",),
        configuration_hash="c" * 64,
        result_hash="d" * 64,
        correlation_id="manual-test",
        causation_id=None,
        experiment_run_id=None,
        decision_source=TradeDecisionSource.MANUAL_OVERRIDE,
        override_reason="Quiero probar la hipótesis contraria.",
        idempotency_key="manual-test-key",
        side=PositionSide.YES,
    )

    assert decision.decision_source is TradeDecisionSource.MANUAL_OVERRIDE
    assert decision.override_reason is not None


def test_manual_decision_without_reason_is_rejected() -> None:
    with pytest.raises(PaperTradingInvariantError, match="reason"):
        TradeDecision(
            decision_id=UUID("00000000-0000-4000-8000-000000000921"),
            prediction_run_id=UUID("00000000-0000-4000-8000-000000000922"),
            portfolio_id=PORTFOLIO_ID,
            decided_at=NOW,
            decision=TradeDecisionType.REJECTED,
            market_probability=Decimal("0.60"),
            system_probability=Decimal("0.55"),
            edge=Decimal("-0.05"),
            confidence=Decimal("0.20"),
            opportunity_level="none",
            proposed_stake=Decimal("1"),
            approved_stake=Decimal("0"),
            rejection_reasons=("market_closed_or_resolved",),
            risk_checks=(),
            configuration_hash="e" * 64,
            result_hash="f" * 64,
            correlation_id="manual-test",
            causation_id=None,
            experiment_run_id=None,
            decision_source=TradeDecisionSource.MANUAL_OVERRIDE,
            override_reason=None,
            idempotency_key="manual-test-key-2",
            side=PositionSide.YES,
        )
