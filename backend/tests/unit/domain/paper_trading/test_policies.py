from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from predictionlab.domain.paper_trading import (
    ConfidenceAdjustedSizing,
    ConservativeCostModel,
    ConservativeRiskPolicy,
    EntryContext,
    ExecutionContext,
    FixedFractionSizing,
    PositionSide,
    PositionSizingConfiguration,
    PositionSizingContext,
    RiskContext,
    ThresholdEntryPolicy,
    TradeDecisionType,
    ZeroCostModel,
)
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus


def entry_context(**overrides: object) -> EntryContext:
    values: dict[str, object] = {
        "prediction_status": PredictionRunStatus.COMPLETED,
        "market_is_open": True,
        "market_probability": Decimal("0.45"),
        "system_probability": Decimal("0.60"),
        "yes_edge": Decimal("0.15"),
        "confidence": Decimal("0.80"),
        "opportunity_level": OpportunityLevel.STRONG,
        "data_age": timedelta(minutes=5),
        "has_existing_position": False,
        "data_complete": True,
    }
    values.update(overrides)
    return EntryContext(**values)  # type: ignore[arg-type]


def test_threshold_policy_supports_yes_no_abstention_and_explicit_rejection() -> None:
    policy = ThresholdEntryPolicy()

    yes = policy.evaluate(entry_context())
    no = policy.evaluate(
        entry_context(
            market_probability=Decimal("0.65"),
            system_probability=Decimal("0.40"),
            yes_edge=Decimal("-0.25"),
        )
    )
    abstained = policy.evaluate(
        entry_context(prediction_status=PredictionRunStatus.ABSTAINED)
    )
    rejected = policy.evaluate(
        entry_context(
            data_age=timedelta(days=3),
            has_existing_position=True,
        )
    )

    assert (yes.decision, yes.side) == (
        TradeDecisionType.BUY_YES,
        PositionSide.YES,
    )
    assert (no.decision, no.side) == (
        TradeDecisionType.BUY_NO,
        PositionSide.NO,
    )
    assert abstained.decision is TradeDecisionType.ABSTAIN
    assert "stale_observation" in rejected.rejection_reasons
    assert "incompatible_existing_position" in rejected.rejection_reasons


def test_sizing_and_risk_caps_are_conservative() -> None:
    configuration = PositionSizingConfiguration()
    fixed = FixedFractionSizing(configuration)
    adjusted = ConfidenceAdjustedSizing(configuration)
    sizing_context = PositionSizingContext(
        equity=Decimal("100"),
        confidence=Decimal("0.50"),
        disagreement=Decimal("0.20"),
        liquidity=Decimal("10"),
        data_age=timedelta(days=2),
    )

    assert fixed.size(sizing_context) == Decimal("1.00000000")
    assert adjusted.size(sizing_context) == Decimal("0.50000000")

    approved = ConservativeRiskPolicy(configuration).assess(
        RiskContext(
            equity=Decimal("100"),
            cash_balance=Decimal("100"),
            total_exposure=Decimal("0"),
            market_exposure=Decimal("0"),
            category_exposure=Decimal("0"),
            proposed_stake=Decimal("1"),
        )
    )
    rejected = ConservativeRiskPolicy(configuration).assess(
        RiskContext(
            equity=Decimal("100"),
            cash_balance=Decimal("100"),
            total_exposure=Decimal("50"),
            market_exposure=Decimal("2"),
            category_exposure=Decimal("15"),
            proposed_stake=Decimal("1"),
        )
    )

    assert approved.approved_stake == Decimal("1")
    assert rejected.approved_stake == Decimal("0")
    assert "maximum_market_exposure" in rejected.rejection_reasons
    assert "category_concentration" in rejected.rejection_reasons
    assert "maximum_total_exposure" in rejected.rejection_reasons


def test_cost_models_never_create_hidden_capital() -> None:
    context = ExecutionContext(
        side=PositionSide.YES,
        market_probability=Decimal("0.40"),
        approved_stake=Decimal("1"),
        liquidity=Decimal("10"),
        data_age=timedelta(days=2),
    )

    zero = ZeroCostModel().execute(context)
    conservative = ConservativeCostModel().execute(context)

    assert zero.net_cost == Decimal("1.00000000")
    assert zero.maximum_loss == zero.net_cost
    assert conservative.net_cost <= context.approved_stake
    assert conservative.fees > 0
    assert conservative.slippage_cost > 0
    assert conservative.effective_probability > conservative.entry_probability
