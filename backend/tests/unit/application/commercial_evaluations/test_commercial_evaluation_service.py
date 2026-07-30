from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from predictionlab.application.commercial_evaluations import (
    CommercialEvaluationService,
    EvaluateCommercialOpportunity,
)
from predictionlab.domain.commercial_evaluations import (
    CommercialLabel,
    DataFreshnessStatus,
    PotentialSide,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    PredictionRunStatus,
)

NOW = datetime(2026, 7, 30, 12, tzinfo=UTC)
PREDICTION_ID = UUID("00000000-0000-4000-8000-000000001201")
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000001202")
EVALUATION_ID = UUID("00000000-0000-4000-8000-000000001203")


def service(*, minimum_net_edge: str = "0.015") -> CommercialEvaluationService:
    return CommercialEvaluationService(
        campaign_id="experimental-v1",
        minimum_net_edge=Decimal(minimum_net_edge),
        minimum_confidence=Decimal("0.45"),
        maximum_data_age=timedelta(days=2),
        percentage_fee=Decimal("0.003"),
        fixed_fee=Decimal("0.001"),
        slippage_probability_points=Decimal("0.004"),
        low_liquidity_penalty_points=Decimal("0.002"),
        stale_observation_penalty_points=Decimal("0.001"),
        low_liquidity_threshold=Decimal("25"),
        cost_stale_after=timedelta(days=1),
        id_factory=lambda: EVALUATION_ID,
    )


def command(**changes: object) -> EvaluateCommercialOpportunity:
    value = EvaluateCommercialOpportunity(
        prediction_run_id=PREDICTION_ID,
        portfolio_id=PORTFOLIO_ID,
        evaluated_at=NOW,
        prediction_status=PredictionRunStatus.PREDICTED,
        estimated_outcome=EstimatedOutcome.YES,
        market_probability=Decimal("0.70"),
        consensus_probability=Decimal("0.80"),
        confidence=Decimal("0.70"),
        market_is_open=True,
        data_age=timedelta(hours=2),
        liquidity=Decimal("100"),
        proposed_stake=Decimal("1"),
        portfolio_is_active=True,
        portfolio_has_open_position=False,
    )
    return replace(value, **changes)


def test_buy_yes_edge_and_costs_produce_actionable_evaluation() -> None:
    evaluation = service().evaluate(command())

    assert evaluation.potential_side is PotentialSide.BUY_YES
    assert evaluation.gross_edge == Decimal("0.10")
    assert evaluation.estimated_fees == Decimal("0.004")
    assert evaluation.estimated_slippage == Decimal("0.004")
    assert evaluation.estimated_other_costs == Decimal("0")
    assert evaluation.net_edge == Decimal("0.092")
    assert evaluation.commercial_label is CommercialLabel.ACTIONABLE
    assert evaluation.is_actionable is True


def test_buy_no_uses_binary_complement_edge() -> None:
    evaluation = service().evaluate(
        command(
            market_probability=Decimal("0.80"),
            consensus_probability=Decimal("0.70"),
        )
    )

    assert evaluation.estimated_outcome is EstimatedOutcome.YES
    assert evaluation.potential_side is PotentialSide.BUY_NO
    assert evaluation.gross_edge == Decimal("0.10")


def test_zero_edge_is_prediction_but_not_actionable() -> None:
    evaluation = service().evaluate(
        command(consensus_probability=Decimal("0.70"))
    )

    assert evaluation.potential_side is PotentialSide.NONE
    assert evaluation.gross_edge == Decimal("0")
    assert evaluation.commercial_label is CommercialLabel.NOT_ACTIONABLE
    assert "no_commercial_edge" in evaluation.reasons


def test_stale_or_unavailable_prediction_is_not_evaluable() -> None:
    evaluation = service().evaluate(
        command(
            prediction_status=PredictionRunStatus.ABSTAINED,
            estimated_outcome=None,
            consensus_probability=None,
            data_age=timedelta(days=3),
        )
    )

    assert evaluation.commercial_label is CommercialLabel.NOT_EVALUABLE
    assert evaluation.potential_side is PotentialSide.NONE
    assert evaluation.data_freshness_status is DataFreshnessStatus.STALE
    assert "prediction_unavailable" in evaluation.reasons
    assert "stale_observation" in evaluation.reasons


def test_risk_and_campaign_failures_are_explicit() -> None:
    evaluation = service().evaluate(
        command(
            portfolio_has_open_position=True,
            campaign_is_active=False,
            risk_reasons=("insufficient_capital",),
        )
    )

    assert evaluation.commercial_label is CommercialLabel.NOT_ACTIONABLE
    assert "campaign_inactive" in evaluation.reasons
    assert "incompatible_existing_position" in evaluation.reasons
    assert "insufficient_capital" in evaluation.reasons
