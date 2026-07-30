"""Compute immutable commercial evaluations without executing a trade."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from predictionlab.application.commercial_evaluations.models import (
    EvaluateCommercialOpportunity,
)
from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.commercial_evaluations import (
    CommercialEvaluation,
    CommercialLabel,
    DataFreshnessStatus,
    PotentialSide,
)
from predictionlab.domain.predictions import PredictionRunStatus

_ZERO = Decimal("0")
_ONE = Decimal("1")


class CommercialEvaluationService:
    def __init__(
        self,
        *,
        campaign_id: str,
        minimum_net_edge: Decimal,
        minimum_confidence: Decimal,
        maximum_data_age: timedelta,
        percentage_fee: Decimal,
        fixed_fee: Decimal,
        slippage_probability_points: Decimal,
        low_liquidity_penalty_points: Decimal,
        stale_observation_penalty_points: Decimal,
        low_liquidity_threshold: Decimal,
        cost_stale_after: timedelta,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        if not campaign_id.strip():
            raise ValueError("campaign_id cannot be blank")
        for value, name in (
            (minimum_net_edge, "minimum_net_edge"),
            (minimum_confidence, "minimum_confidence"),
            (percentage_fee, "percentage_fee"),
            (slippage_probability_points, "slippage_probability_points"),
            (low_liquidity_penalty_points, "low_liquidity_penalty_points"),
            (
                stale_observation_penalty_points,
                "stale_observation_penalty_points",
            ),
        ):
            _probability(value, name)
        if fixed_fee < 0:
            raise ValueError("fixed_fee cannot be negative")
        if low_liquidity_threshold < 0:
            raise ValueError("low_liquidity_threshold cannot be negative")
        if maximum_data_age <= timedelta(0) or cost_stale_after <= timedelta(0):
            raise ValueError("data-age limits must be positive")
        self.campaign_id = campaign_id.strip()
        self.minimum_net_edge = minimum_net_edge
        self.minimum_confidence = minimum_confidence
        self.maximum_data_age = maximum_data_age
        self.percentage_fee = percentage_fee
        self.fixed_fee = fixed_fee
        self.slippage_probability_points = slippage_probability_points
        self.low_liquidity_penalty_points = low_liquidity_penalty_points
        self.stale_observation_penalty_points = stale_observation_penalty_points
        self.low_liquidity_threshold = low_liquidity_threshold
        self.cost_stale_after = cost_stale_after
        self._id_factory = id_factory
        self.configuration_hash = canonical_sha256(
            {
                "service": "commercial_evaluation",
                "version": "1.0.0",
                "campaign_id": self.campaign_id,
                "minimum_net_edge": minimum_net_edge,
                "minimum_confidence": minimum_confidence,
                "maximum_data_age_seconds": int(maximum_data_age.total_seconds()),
                "percentage_fee": percentage_fee,
                "fixed_fee": fixed_fee,
                "slippage_probability_points": slippage_probability_points,
                "low_liquidity_penalty_points": low_liquidity_penalty_points,
                "stale_observation_penalty_points": (
                    stale_observation_penalty_points
                ),
                "low_liquidity_threshold": low_liquidity_threshold,
                "cost_stale_after_seconds": int(cost_stale_after.total_seconds()),
            }
        )

    def evaluate(
        self,
        command: EvaluateCommercialOpportunity,
    ) -> CommercialEvaluation:
        not_evaluable: list[str] = []
        if command.prediction_status not in {
            PredictionRunStatus.PREDICTED,
            PredictionRunStatus.COMPLETED,
        }:
            not_evaluable.append("prediction_unavailable")
        if not command.market_is_open:
            not_evaluable.append("market_closed_or_resolved")
        if (
            command.market_probability is None
            or command.consensus_probability is None
            or command.estimated_outcome is None
        ):
            not_evaluable.append("incomplete_prediction")
        if command.data_age is None:
            freshness = DataFreshnessStatus.UNAVAILABLE
            not_evaluable.append("missing_observation")
        elif command.data_age > self.maximum_data_age:
            freshness = DataFreshnessStatus.STALE
            not_evaluable.append("stale_observation")
        else:
            freshness = DataFreshnessStatus.FRESH

        potential_side = PotentialSide.NONE
        gross_edge: Decimal | None = None
        estimated_fees = _ZERO
        estimated_slippage = _ZERO
        estimated_other_costs = _ZERO
        net_edge: Decimal | None = None
        if (
            command.market_probability is not None
            and command.consensus_probability is not None
        ):
            yes_edge = command.consensus_probability - command.market_probability
            if yes_edge > 0:
                potential_side = PotentialSide.BUY_YES
                gross_edge = yes_edge
            elif yes_edge < 0:
                potential_side = PotentialSide.BUY_NO
                gross_edge = -yes_edge
            else:
                gross_edge = _ZERO
            if potential_side is not PotentialSide.NONE:
                estimated_fees = self.percentage_fee
                if command.proposed_stake > 0 and self.fixed_fee > 0:
                    estimated_fees += min(
                        self.fixed_fee / command.proposed_stake,
                        _ONE,
                    )
                estimated_slippage = self.slippage_probability_points
                if (
                    command.liquidity is not None
                    and command.liquidity < self.low_liquidity_threshold
                ):
                    estimated_other_costs += self.low_liquidity_penalty_points
                if (
                    command.data_age is not None
                    and command.data_age > self.cost_stale_after
                ):
                    estimated_other_costs += (
                        self.stale_observation_penalty_points
                    )
                net_edge = gross_edge - (
                    estimated_fees
                    + estimated_slippage
                    + estimated_other_costs
                )

        reasons: list[str]
        if not_evaluable:
            label = CommercialLabel.NOT_EVALUABLE
            potential_side = PotentialSide.NONE
            reasons = list(dict.fromkeys(not_evaluable))
        else:
            reasons = [
                *command.entry_reasons,
                *command.risk_reasons,
            ]
            if not command.campaign_is_active:
                reasons.append("campaign_inactive")
            if not command.portfolio_is_active:
                reasons.append("portfolio_inactive")
            if command.portfolio_has_open_position:
                reasons.append("incompatible_existing_position")
            if command.confidence < self.minimum_confidence:
                reasons.append("insufficient_confidence")
            if potential_side is PotentialSide.NONE or gross_edge == 0:
                reasons.append("no_commercial_edge")
            if net_edge is None or net_edge < self.minimum_net_edge:
                reasons.append("insufficient_net_edge")
            reasons = list(dict.fromkeys(reasons))
            label = (
                CommercialLabel.NOT_ACTIONABLE
                if reasons
                else CommercialLabel.ACTIONABLE
            )
            if not reasons:
                reasons.append("commercial_thresholds_passed")

        evaluation_id: UUID = self._id_factory()
        result_payload = {
            "prediction_run_id": command.prediction_run_id,
            "portfolio_id": command.portfolio_id,
            "campaign_id": self.campaign_id,
            "evaluated_at": command.evaluated_at,
            "estimated_outcome": command.estimated_outcome,
            "potential_side": potential_side,
            "market_probability": command.market_probability,
            "consensus_probability": command.consensus_probability,
            "gross_edge": gross_edge,
            "estimated_fees": estimated_fees,
            "estimated_slippage": estimated_slippage,
            "estimated_other_costs": estimated_other_costs,
            "net_edge": net_edge,
            "confidence": command.confidence,
            "commercial_label": label,
            "reasons": tuple(reasons),
            "warnings": command.warnings,
            "configuration_hash": self.configuration_hash,
            "portfolio_has_open_position": (
                command.portfolio_has_open_position
            ),
            "data_freshness_status": freshness,
        }
        return CommercialEvaluation(
            evaluation_id=evaluation_id,
            prediction_run_id=command.prediction_run_id,
            portfolio_id=command.portfolio_id,
            campaign_id=self.campaign_id,
            evaluated_at=command.evaluated_at,
            estimated_outcome=command.estimated_outcome,
            potential_side=potential_side,
            market_probability=command.market_probability,
            consensus_probability=command.consensus_probability,
            gross_edge=gross_edge,
            estimated_fees=estimated_fees,
            estimated_slippage=estimated_slippage,
            estimated_other_costs=estimated_other_costs,
            net_edge=net_edge,
            confidence=command.confidence,
            commercial_label=label,
            is_actionable=label is CommercialLabel.ACTIONABLE,
            reasons=tuple(reasons),
            warnings=command.warnings,
            configuration_hash=self.configuration_hash,
            result_hash=canonical_sha256(result_payload),
            created_at=command.evaluated_at,
            portfolio_has_open_position=command.portfolio_has_open_position,
            data_freshness_status=freshness,
        )


def _probability(value: Decimal, name: str) -> None:
    if not value.is_finite() or not _ZERO <= value <= _ONE:
        raise ValueError(f"{name} must be between 0 and 1")
