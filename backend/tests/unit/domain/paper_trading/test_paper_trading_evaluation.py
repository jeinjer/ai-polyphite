from __future__ import annotations

from decimal import Decimal

from predictionlab.domain.paper_trading import (
    MarketFollowBaseline,
    NoTradeBaseline,
    PositionSide,
    SampleEvidenceState,
    TradingSample,
    ZeroCostModel,
    evaluate_baseline,
    evaluate_performance,
)


def sample(
    market_id: str,
    pnl: str | None,
    *,
    side: PositionSide = PositionSide.YES,
) -> TradingSample:
    return TradingSample(
        market_id=market_id,
        category="testing",
        opportunity_level="strong",
        edge=Decimal("0.10"),
        confidence=Decimal("0.80"),
        realized_pnl=Decimal(pnl) if pnl is not None else None,
        costs=Decimal("0.01"),
        outcome="yes" if pnl is not None else None,
        side=side,
    )


def test_performance_reports_financial_and_evidence_metrics() -> None:
    metrics = evaluate_performance(
        initial_capital=Decimal("100"),
        final_equity=Decimal("105"),
        realized_pnl=Decimal("5"),
        unrealized_pnl=Decimal("0"),
        decision_count=4,
        abstention_count=1,
        rejection_count=0,
        open_trade_count=0,
        samples=(sample("one", "7"), sample("two", "-2")),
        equity_curve=(
            Decimal("100"),
            Decimal("90"),
            Decimal("105"),
        ),
        exposure_curve=(Decimal("0"), Decimal("2"), Decimal("0")),
        preliminary_threshold=2,
        observation_threshold=3,
        expansion_threshold=4,
    )

    assert metrics.net_profit == Decimal("5")
    assert metrics.simulated_roi == Decimal("0.05")
    assert metrics.win_rate == Decimal("0.5")
    assert metrics.profit_factor == Decimal("3.5")
    assert metrics.maximum_drawdown == Decimal("0.1")
    assert metrics.coverage == Decimal("0.5")
    assert metrics.evidence_state is SampleEvidenceState.PRELIMINARY


def test_baselines_share_costs_and_refund_cancelled_markets() -> None:
    samples = (sample("cancelled", "0"),)
    common = {
        "samples": samples,
        "market_probabilities": {"cancelled": Decimal("0.60")},
        "system_probabilities": {"cancelled": Decimal("0.70")},
        "outcomes": {"cancelled": "cancelled"},
        "initial_capital": Decimal("100"),
        "stake": Decimal("1"),
        "cost_model": ZeroCostModel(),
    }

    no_trade = evaluate_baseline(baseline=NoTradeBaseline(), **common)
    followed = evaluate_baseline(baseline=MarketFollowBaseline(), **common)

    assert no_trade.final_capital == Decimal("100")
    assert no_trade.trade_count == 0
    assert followed.final_capital == Decimal("100")
    assert followed.trade_count == 1
    assert followed.total_costs == Decimal("0")


def test_cancelled_positions_close_without_polluting_accuracy_evidence() -> None:
    cancelled = TradingSample(
        market_id="cancelled",
        category="testing",
        opportunity_level="strong",
        edge=Decimal("0.10"),
        confidence=Decimal("0.80"),
        realized_pnl=Decimal("0"),
        costs=Decimal("0"),
        outcome="cancelled",
        side=PositionSide.YES,
    )

    metrics = evaluate_performance(
        initial_capital=Decimal("100"),
        final_equity=Decimal("100"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        decision_count=1,
        abstention_count=0,
        rejection_count=0,
        open_trade_count=0,
        samples=(cancelled,),
        equity_curve=(Decimal("100"), Decimal("100")),
        exposure_curve=(Decimal("0"), Decimal("1"), Decimal("0")),
    )

    assert metrics.closed_trade_count == 1
    assert metrics.win_rate is None
    assert metrics.independent_resolved_markets == 0
    assert metrics.evidence_state is SampleEvidenceState.INSUFFICIENT
