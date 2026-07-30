"""Prediction aggregate persisted after a complete agent pipeline."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from predictionlab.domain.agents import AgentPrediction, Recommendation

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class PredictionInvariantError(ValueError):
    pass


class PredictionRunStatus(StrEnum):
    PREDICTED = "predicted"
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    FAILED = "failed"


class EstimatedOutcome(StrEnum):
    YES = "yes"
    NO = "no"


class OpportunityLevel(StrEnum):
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(frozen=True, slots=True, kw_only=True)
class EdgeThresholds:
    weak: Decimal = Decimal("0.03")
    moderate: Decimal = Decimal("0.08")
    strong: Decimal = Decimal("0.15")

    def __post_init__(self) -> None:
        for field_name in ("weak", "moderate", "strong"):
            _probability(getattr(self, field_name), field_name)
        if not self.weak < self.moderate < self.strong:
            raise PredictionInvariantError("edge thresholds must be strictly increasing")

    def classify(self, edge: Decimal) -> OpportunityLevel:
        absolute = abs(edge)
        if absolute < self.weak:
            return OpportunityLevel.NONE
        if absolute < self.moderate:
            return OpportunityLevel.WEAK
        if absolute < self.strong:
            return OpportunityLevel.MODERATE
        return OpportunityLevel.STRONG


@dataclass(frozen=True, slots=True, kw_only=True)
class PredictionPolicy:
    edge_thresholds: EdgeThresholds = field(default_factory=EdgeThresholds)
    minimum_confidence: Decimal = Decimal("0.40")
    maximum_disagreement: Decimal = Decimal("0.30")
    maximum_observation_age_seconds: int = 172_800
    extreme_probability_floor: Decimal = Decimal("0.02")
    extreme_probability_ceiling: Decimal = Decimal("0.98")
    minimum_extreme_observations: int = 3

    def __post_init__(self) -> None:
        _probability(self.minimum_confidence, "minimum_confidence")
        _probability(self.maximum_disagreement, "maximum_disagreement")
        _probability(self.extreme_probability_floor, "extreme_probability_floor")
        _probability(self.extreme_probability_ceiling, "extreme_probability_ceiling")
        if self.extreme_probability_floor >= self.extreme_probability_ceiling:
            raise PredictionInvariantError("extreme probability bounds are invalid")
        if self.maximum_observation_age_seconds <= 0:
            raise PredictionInvariantError("maximum observation age must be positive")
        if self.minimum_extreme_observations < 1:
            raise PredictionInvariantError("minimum extreme observations must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class PredictionRun:
    prediction_run_id: UUID
    experiment_run_id: UUID | None
    market_id: UUID
    predicted_at: datetime
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    consensus_confidence: Decimal
    recommendation: Recommendation
    edge: Decimal | None
    no_edge: Decimal | None
    opportunity_level: OpportunityLevel
    disagreement_score: Decimal
    status: PredictionRunStatus
    agent_configuration_hash: str
    input_hash: str
    result_hash: str
    duration_ms: Decimal
    safe_error_type: str | None
    abstention_reason: str | None
    correlation_id: str
    causation_id: str | None
    created_at: datetime
    agent_weights: Mapping[str, Decimal]
    agent_predictions: tuple[AgentPrediction, ...]
    estimated_outcome: EstimatedOutcome | None = None

    def __post_init__(self) -> None:
        for field_name in ("prediction_run_id", "market_id"):
            if getattr(self, field_name).int == 0:
                raise PredictionInvariantError(f"{field_name} must be non-zero")
        object.__setattr__(self, "predicted_at", _utc(self.predicted_at, "predicted_at"))
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        for field_name in ("market_probability", "consensus_probability", "edge", "no_edge"):
            value = getattr(self, field_name)
            if value is not None:
                if field_name in {"edge", "no_edge"}:
                    _edge(value, field_name)
                else:
                    _probability(value, field_name)
        _probability(self.consensus_confidence, "consensus_confidence")
        _probability(self.disagreement_score, "disagreement_score")
        _non_negative(self.duration_ms, "duration_ms")
        for field_name in (
            "agent_configuration_hash",
            "input_hash",
            "result_hash",
        ):
            if not _SHA256_PATTERN.fullmatch(getattr(self, field_name)):
                raise PredictionInvariantError(f"{field_name} must be a SHA-256 digest")
        if not self.correlation_id.strip():
            raise PredictionInvariantError("correlation_id cannot be blank")
        if self.causation_id is not None and not self.causation_id.strip():
            raise PredictionInvariantError("causation_id cannot be blank")
        object.__setattr__(
            self,
            "agent_weights",
            MappingProxyType(dict(self.agent_weights)),
        )
        self._validate_state()

    def _validate_state(self) -> None:
        if self.status is PredictionRunStatus.FAILED:
            if self.safe_error_type is None or not self.safe_error_type.strip():
                raise PredictionInvariantError("failed runs require safe_error_type")
            if self.abstention_reason is not None:
                raise PredictionInvariantError("failed runs cannot have an abstention reason")
            if (
                self.recommendation is not Recommendation.ABSTAIN
                or self.consensus_probability is not None
                or self.edge is not None
                or self.no_edge is not None
            ):
                raise PredictionInvariantError(
                    "failed runs cannot publish a recommendation or probabilities"
                )
            return
        if self.safe_error_type is not None:
            raise PredictionInvariantError("successful runs cannot have safe_error_type")
        if self.status is PredictionRunStatus.ABSTAINED:
            if self.recommendation is not Recommendation.ABSTAIN:
                raise PredictionInvariantError("abstained run requires abstain recommendation")
            if self.consensus_probability is not None or self.edge is not None:
                raise PredictionInvariantError("abstained run cannot publish probability or edge")
            if self.abstention_reason is None or not self.abstention_reason.strip():
                raise PredictionInvariantError("abstained run requires an explicit reason")
            return
        if self.status not in {
            PredictionRunStatus.PREDICTED,
            PredictionRunStatus.COMPLETED,
        }:
            raise PredictionInvariantError("unsupported successful prediction status")
        if self.recommendation is Recommendation.ABSTAIN:
            raise PredictionInvariantError("successful run cannot abstain")
        if (
            self.market_probability is None
            or self.consensus_probability is None
            or self.edge is None
            or self.no_edge is None
        ):
            raise PredictionInvariantError("completed run requires probabilities and edges")
        if self.edge != self.consensus_probability - self.market_probability:
            raise PredictionInvariantError("edge is inconsistent")
        if self.no_edge != -self.edge:
            raise PredictionInvariantError("no_edge must be the opposite YES edge")
        if self.abstention_reason is not None:
            raise PredictionInvariantError("successful run cannot have an abstention reason")
        if self.status is PredictionRunStatus.PREDICTED:
            if self.estimated_outcome is None:
                raise PredictionInvariantError("predicted run requires an estimated outcome")
            expected = (
                EstimatedOutcome.YES
                if self.consensus_probability >= Decimal("0.5")
                else EstimatedOutcome.NO
            )
            if self.estimated_outcome is not expected:
                raise PredictionInvariantError(
                    "estimated outcome is inconsistent with consensus probability"
                )
        elif self.estimated_outcome is not None:
            expected = (
                EstimatedOutcome.YES
                if self.consensus_probability >= Decimal("0.5")
                else EstimatedOutcome.NO
            )
            if self.estimated_outcome is not expected:
                raise PredictionInvariantError(
                    "estimated outcome is inconsistent with consensus probability"
                )


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PredictionInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _probability(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if not Decimal("0") <= value <= Decimal("1"):
        raise PredictionInvariantError(f"{field_name} must be between 0 and 1")


def _edge(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if not Decimal("-1") <= value <= Decimal("1"):
        raise PredictionInvariantError(f"{field_name} must be between -1 and 1")


def _non_negative(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if value < 0:
        raise PredictionInvariantError(f"{field_name} cannot be negative")


def _decimal(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PredictionInvariantError(f"{field_name} must be a finite Decimal")
