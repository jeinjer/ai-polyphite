"""Application commands and read models for predictions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from predictionlab.domain.agents import (
    AgentEvidence,
    AgentObservation,
    JsonScalar,
    Recommendation,
)
from predictionlab.domain.commercial_evaluations import (
    CommercialEvaluation,
    CommercialLabel,
    DataFreshnessStatus,
    PotentialSide,
)
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome
from predictionlab.domain.paper_trading import (
    PositionSide,
    TradeDecisionSource,
    TradeDecisionType,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    OpportunityLevel,
    PredictionRunStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketPredictionSnapshot:
    market_id: UUID
    title: str
    description: str | None
    category: str | None
    status: MarketStatus
    resolution_at: datetime | None
    observations: tuple[AgentObservation, ...]

    @property
    def latest_probability(self) -> Decimal | None:
        return next(
            (
                item.probability
                for item in reversed(self.observations)
                if item.probability is not None
            ),
            None,
        )

    @property
    def latest_volume(self) -> Decimal | None:
        return next(
            (item.volume for item in reversed(self.observations) if item.volume is not None),
            None,
        )

    @property
    def latest_liquidity(self) -> Decimal | None:
        return next(
            (item.liquidity for item in reversed(self.observations) if item.liquidity is not None),
            None,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RunPrediction:
    market_id: UUID
    predicted_at: datetime
    experiment_run_id: UUID | None = None
    random_seed: int = 0
    context: dict[str, JsonScalar] = field(default_factory=dict)
    model_configuration: dict[str, JsonScalar] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if self.predicted_at.tzinfo is None or self.predicted_at.utcoffset() is None:
            raise ValueError("predicted_at must be timezone-aware")
        object.__setattr__(self, "predicted_at", self.predicted_at.astimezone(UTC))
        if self.random_seed < 0:
            raise ValueError("random_seed cannot be negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentPredictionDetail:
    agent_prediction_id: UUID
    agent_name: str
    agent_version: str
    predicted_probability: Decimal | None
    confidence: Decimal
    recommendation: Recommendation
    rationale_summary: str
    evidence: tuple[AgentEvidence, ...]
    warnings: tuple[str, ...]
    input_hash: str
    output_hash: str
    duration_ms: Decimal
    disagreement_score: Decimal | None
    agent_weights: dict[str, Decimal]


@dataclass(frozen=True, slots=True, kw_only=True)
class PredictionRunDetail:
    prediction_run_id: UUID
    experiment_run_id: UUID | None
    market_id: UUID
    market_title: str
    category: str | None
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
    agent_weights: dict[str, Decimal]
    agent_predictions: tuple[AgentPredictionDetail, ...]
    estimated_outcome: EstimatedOutcome | None = None
    market_status: MarketStatus | None = None
    provider_code: str | None = None
    commercial_evaluation: CommercialEvaluation | None = None
    related_executions: tuple[RelatedPaperExecution, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedPaperExecution:
    decision_id: UUID
    portfolio_id: UUID
    portfolio_name: str
    decision: TradeDecisionType
    decision_source: TradeDecisionSource
    override_reason: str | None
    side: PositionSide | None
    decided_at: datetime
    order_id: UUID | None
    trade_id: UUID | None
    position_id: UUID | None


class PredictionSort(StrEnum):
    PREDICTED_AT = "predicted_at"
    MARKET_PROBABILITY = "market_probability"
    CONSENSUS_PROBABILITY = "consensus_probability"
    CONSENSUS_CONFIDENCE = "consensus_confidence"
    NET_EDGE = "net_edge"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class EstimatedOutcomeFilter(StrEnum):
    YES = "yes"
    NO = "no"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True, kw_only=True)
class PredictionListItem:
    prediction_run_id: UUID
    market_id: UUID
    market_title: str
    provider_code: str
    category: str | None
    predicted_at: datetime
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    consensus_confidence: Decimal
    estimated_outcome: EstimatedOutcome | None
    commercial_label: CommercialLabel
    potential_side: PotentialSide
    gross_edge: Decimal | None
    net_edge: Decimal | None
    is_actionable: bool
    primary_reason: str
    portfolio_has_open_position: bool
    data_freshness_status: DataFreshnessStatus
    campaign_id: str | None
    portfolio_id: UUID | None


@dataclass(frozen=True, slots=True)
class PredictionListPage:
    items: tuple[PredictionListItem, ...]
    page: int
    page_size: int
    total_items: int
    applied_filters: dict[str, str]

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True, kw_only=True)
class ListPredictions:
    page: int = 1
    page_size: int = 20
    predicted_from: datetime | None = None
    predicted_to: datetime | None = None
    market_id: UUID | None = None
    category: str | None = None
    recommendation: Recommendation | None = None
    status: PredictionRunStatus | None = None
    opportunity_level: OpportunityLevel | None = None
    experiment_run_id: UUID | None = None
    provider: str | None = None
    commercial_label: CommercialLabel | None = None
    estimated_outcome_filter: EstimatedOutcomeFilter | None = None
    portfolio_id: UUID | None = None
    campaign_id: str | None = None
    sort: PredictionSort = PredictionSort.PREDICTED_AT
    direction: SortDirection = SortDirection.DESC

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be positive")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if (
            self.predicted_from is not None
            and self.predicted_to is not None
            and self.predicted_from > self.predicted_to
        ):
            raise ValueError("predicted_from cannot be after predicted_to")
        if self.category is not None and not self.category.strip():
            raise ValueError("category cannot be blank")
        if self.provider is not None and not self.provider.strip():
            raise ValueError("provider cannot be blank")
        if self.campaign_id is not None and not self.campaign_id.strip():
            raise ValueError("campaign_id cannot be blank")


@dataclass(frozen=True, slots=True)
class PredictionRunPage:
    items: tuple[PredictionRunDetail, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return 0 if self.total == 0 else (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedPredictionSample:
    prediction_run_id: UUID
    market_id: UUID
    predicted_at: datetime
    system_probability: Decimal | None
    market_probability: Decimal
    recommendation: Recommendation
    status: PredictionRunStatus
    outcome: ResolutionOutcome

    @property
    def binary_outcome(self) -> Decimal:
        if self.outcome is ResolutionOutcome.YES:
            return Decimal("1")
        if self.outcome is ResolutionOutcome.NO:
            return Decimal("0")
        raise ValueError("sample does not have a binary outcome")


@dataclass(frozen=True, slots=True)
class MetricSummary:
    brier_score: Decimal
    log_loss: Decimal
    absolute_error: Decimal
    directional_accuracy: Decimal


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    lower_bound: Decimal
    upper_bound: Decimal
    prediction_count: int
    mean_probability: Decimal
    observed_frequency: Decimal


@dataclass(frozen=True, slots=True)
class PredictionEvaluationReport:
    experiment_run_id: UUID | None
    resolved_count: int
    emitted_count: int
    abstained_count: int
    coverage: Decimal
    system: MetricSummary | None
    market_baseline: MetricSummary | None
    constant_baseline: MetricSummary | None
    calibration: tuple[CalibrationBucket, ...]
