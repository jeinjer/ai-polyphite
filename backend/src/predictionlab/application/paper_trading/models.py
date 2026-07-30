"""Commands and read models for simulated portfolio research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from predictionlab.domain.commercial_evaluations import CommercialEvaluation
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome
from predictionlab.domain.paper_trading import (
    BaselinePerformance,
    CurrencyUnit,
    PaperOrder,
    PaperPerformanceMetrics,
    PaperPerformanceSnapshot,
    PaperPortfolio,
    PaperPortfolioStatus,
    PaperPosition,
    PaperPositionStatus,
    PaperSettlement,
    PaperTrade,
    PositionSide,
    TradeDecision,
    TradeDecisionSource,
    TradeDecisionType,
    TradingSample,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    OpportunityLevel,
    PredictionRunStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePaperPortfolio:
    name: str
    currency_unit: CurrencyUnit
    initial_balance: Decimal
    experiment_run_id: UUID | None = None
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class CreatePaperPortfolioResult:
    portfolio: PaperPortfolio
    created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RunPaperTrading:
    portfolio_id: UUID
    prediction_run_id: UUID
    decided_at: datetime | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if self.decided_at is not None:
            object.__setattr__(
                self,
                "decided_at",
                _utc(self.decided_at, "decided_at"),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RunManualPaperTrade:
    portfolio_id: UUID
    prediction_run_id: UUID
    side: PositionSide
    requested_stake: Decimal
    override_reason: str
    idempotency_key: str
    decided_at: datetime | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if self.requested_stake <= 0:
            raise ValueError("requested_stake must be positive")
        if not self.override_reason.strip():
            raise ValueError("override_reason cannot be blank")
        if len(self.override_reason.strip()) > 1000:
            raise ValueError("override_reason cannot exceed 1000 characters")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key cannot be blank")
        if len(self.idempotency_key.strip()) > 200:
            raise ValueError("idempotency_key cannot exceed 200 characters")
        object.__setattr__(self, "override_reason", self.override_reason.strip())
        object.__setattr__(self, "idempotency_key", self.idempotency_key.strip())
        if self.decided_at is not None:
            object.__setattr__(
                self,
                "decided_at",
                _utc(self.decided_at, "decided_at"),
            )


class ManualPaperTradeStatus(StrEnum):
    FILLED = "filled"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True, kw_only=True)
class SettlePaperPortfolio:
    portfolio_id: UUID
    settled_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "settled_at",
            _utc(self.settled_at, "settled_at"),
        )


@dataclass(frozen=True, slots=True)
class PaperTradingOutcome:
    decision: TradeDecision
    order: PaperOrder | None
    trade: PaperTrade | None
    position: PaperPosition | None
    commercial_evaluation: CommercialEvaluation | None = None

    @property
    def artifact_hashes(self) -> tuple[str, ...]:
        values = [self.decision.result_hash]
        if self.trade is not None:
            values.append(self.trade.result_hash)
        if self.commercial_evaluation is not None:
            values.append(self.commercial_evaluation.result_hash)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class ManualPaperTradeResult:
    status: ManualPaperTradeStatus
    outcome: PaperTradingOutcome


@dataclass(frozen=True, slots=True)
class SettlementBatchResult:
    settlements: tuple[PaperSettlement, ...]
    performance_snapshot: PaperPerformanceSnapshot

    @property
    def artifact_hashes(self) -> tuple[str, ...]:
        return (
            *(item.result_hash for item in self.settlements),
            self.performance_snapshot.result_hash,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TradingPredictionContext:
    prediction_run_id: UUID
    prediction_result_hash: str
    experiment_run_id: UUID | None
    market_id: UUID
    market_title: str
    category: str | None
    predicted_at: datetime
    prediction_status: PredictionRunStatus
    market_probability: Decimal | None
    system_probability: Decimal | None
    edge: Decimal | None
    confidence: Decimal
    opportunity_level: OpportunityLevel
    disagreement_score: Decimal
    market_status_as_of: MarketStatus
    observation_at: datetime | None
    liquidity: Decimal | None
    estimated_outcome: EstimatedOutcome | None = None


@dataclass(frozen=True, slots=True)
class PortfolioExposure:
    total: Decimal
    market: Decimal
    category: Decimal


@dataclass(frozen=True, slots=True)
class OpenPositionContext:
    position: PaperPosition
    market_status: MarketStatus
    resolution_outcome: ResolutionOutcome
    resolved_at: datetime | None
    latest_probability: Decimal | None
    observation_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ListPaperPortfolios:
    page: int = 1
    page_size: int = 20
    status: PaperPortfolioStatus | None = None
    experiment_run_id: UUID | None = None
    currency_unit: CurrencyUnit | None = None

    def __post_init__(self) -> None:
        _page(self.page, self.page_size)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListTradeDecisions:
    page: int = 1
    page_size: int = 20
    portfolio_id: UUID | None = None
    market_id: UUID | None = None
    category: str | None = None
    side: PositionSide | None = None
    decision: TradeDecisionType | None = None
    opportunity_level: OpportunityLevel | None = None
    experiment_run_id: UUID | None = None
    decided_from: datetime | None = None
    decided_to: datetime | None = None

    def __post_init__(self) -> None:
        _page(self.page, self.page_size)
        _range(self.decided_from, self.decided_to)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListPaperTrades:
    page: int = 1
    page_size: int = 20
    portfolio_id: UUID | None = None
    market_id: UUID | None = None
    category: str | None = None
    side: PositionSide | None = None
    experiment_run_id: UUID | None = None
    executed_from: datetime | None = None
    executed_to: datetime | None = None

    def __post_init__(self) -> None:
        _page(self.page, self.page_size)
        _range(self.executed_from, self.executed_to)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListPaperPositions:
    page: int = 1
    page_size: int = 20
    portfolio_id: UUID | None = None
    market_id: UUID | None = None
    category: str | None = None
    side: PositionSide | None = None
    status: PaperPositionStatus | None = None
    experiment_run_id: UUID | None = None

    def __post_init__(self) -> None:
        _page(self.page, self.page_size)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListPaperSettlements:
    page: int = 1
    page_size: int = 20
    portfolio_id: UUID | None = None
    market_id: UUID | None = None
    outcome: ResolutionOutcome | None = None
    experiment_run_id: UUID | None = None
    resolved_from: datetime | None = None
    resolved_to: datetime | None = None

    def __post_init__(self) -> None:
        _page(self.page, self.page_size)
        _range(self.resolved_from, self.resolved_to)


@dataclass(frozen=True, slots=True)
class PaperPage[T]:
    items: tuple[T, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return 0 if self.total == 0 else (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPortfolioDetail:
    portfolio_id: UUID
    name: str
    currency_unit: CurrencyUnit
    initial_balance: Decimal
    cash_balance: Decimal
    reserved_balance: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    total_exposure: Decimal
    status: PaperPortfolioStatus
    strategy_configuration_hash: str
    experiment_run_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeDecisionDetail:
    decision_id: UUID
    prediction_run_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    decided_at: datetime
    decision: TradeDecisionType
    side: PositionSide | None
    market_probability: Decimal | None
    system_probability: Decimal | None
    edge: Decimal | None
    confidence: Decimal
    opportunity_level: OpportunityLevel
    proposed_stake: Decimal
    approved_stake: Decimal
    rejection_reasons: tuple[str, ...]
    risk_checks: tuple[str, ...]
    configuration_hash: str
    result_hash: str
    correlation_id: str
    causation_id: str | None
    experiment_run_id: UUID | None
    prediction_result_hash: str
    decision_source: TradeDecisionSource
    override_reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperTradeDetail:
    trade_id: UUID
    order_id: UUID
    decision_id: UUID
    portfolio_id: UUID
    prediction_run_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    executed_at: datetime
    side: PositionSide
    entry_probability: Decimal
    effective_probability: Decimal
    units: Decimal
    gross_cost: Decimal
    fees: Decimal
    slippage_cost: Decimal
    net_cost: Decimal
    maximum_loss: Decimal
    potential_payout: Decimal
    execution_model: str
    result_hash: str
    decision_reasons: tuple[str, ...]
    prediction_result_hash: str
    experiment_run_id: UUID | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPositionDetail:
    position_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    side: PositionSide
    opened_at: datetime
    closed_at: datetime | None
    status: PaperPositionStatus
    units: Decimal
    average_entry_probability: Decimal
    invested_amount: Decimal
    current_mark_probability: Decimal | None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    settlement_outcome: ResolutionOutcome | None
    prediction_run_id: UUID
    trade_id: UUID
    opportunity_level: OpportunityLevel
    entry_edge: Decimal
    entry_confidence: Decimal
    experiment_run_id: UUID | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperSettlementDetail:
    settlement_id: UUID
    position_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    resolved_at: datetime
    outcome: ResolutionOutcome
    gross_payout: Decimal
    fees: Decimal
    net_payout: Decimal
    realized_pnl: Decimal
    settlement_policy: str
    result_hash: str
    created_at: datetime
    correlation_id: str
    causation_id: str | None
    experiment_run_id: UUID | None


@dataclass(frozen=True, slots=True, kw_only=True)
class EquityCurvePoint:
    recorded_at: datetime
    equity: Decimal
    drawdown: Decimal
    exposure: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    cumulative_costs: Decimal
    result_hash: str


@dataclass(frozen=True, slots=True)
class SimulationAlert:
    code: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPerformanceData:
    portfolio: PaperPortfolioDetail
    decision_count: int
    abstention_count: int
    rejection_count: int
    open_position_count: int
    samples: tuple[TradingSample, ...]
    baseline_samples: tuple[TradingSample, ...]
    equity_curve: tuple[EquityCurvePoint, ...]
    market_probabilities: dict[str, Decimal]
    system_probabilities: dict[str, Decimal]
    outcomes: dict[str, str]
    maximum_category_concentration: Decimal
    consecutive_losses: int
    unsettled_resolved_count: int
    other_pending_count: int
    stale_open_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPerformanceReport:
    portfolio: PaperPortfolioDetail
    metrics: PaperPerformanceMetrics
    baselines: tuple[BaselinePerformance, ...]
    alerts: tuple[SimulationAlert, ...]
    strategy_configuration_hash: str
    simulation_only: bool = True


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _page(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be positive")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")


def _range(start: datetime | None, end: datetime | None) -> None:
    if start is not None:
        _utc(start, "from")
    if end is not None:
        _utc(end, "to")
    if start is not None and end is not None and start > end:
        raise ValueError("from cannot be after to")
