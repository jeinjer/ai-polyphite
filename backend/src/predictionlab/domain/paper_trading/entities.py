"""Auditable entities for long-only binary-contract paper trading."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_TOLERANCE = Decimal("0.00000001")
_AMOUNT_QUANTUM = Decimal("0.00000001")


class PaperTradingInvariantError(ValueError):
    """Raised when simulated accounting would become inconsistent."""


class CurrencyUnit(StrEnum):
    USD_SIMULATED = "USD_SIMULATED"
    MANA_SIMULATED = "MANA_SIMULATED"


class PaperPortfolioStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class TradeDecisionType(StrEnum):
    BUY_YES = "buy_yes"
    BUY_NO = "buy_no"
    ABSTAIN = "abstain"
    REJECTED = "rejected"


class TradeDecisionSource(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL_OVERRIDE = "manual_override"


class PositionSide(StrEnum):
    YES = "yes"
    NO = "no"


class PaperOrderStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaperPositionStatus(StrEnum):
    OPEN = "open"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class LedgerEntryType(StrEnum):
    INITIAL_CAPITAL = "initial_capital"
    POSITION_OPENED = "position_opened"
    SETTLEMENT = "settlement"
    CANCELLATION_REFUND = "cancellation_refund"


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPortfolio:
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

    def __post_init__(self) -> None:
        _uuid(self.portfolio_id, "portfolio_id")
        _text(self.name, "name")
        _positive(self.initial_balance, "initial_balance")
        for field_name in (
            "cash_balance",
            "reserved_balance",
            "equity",
            "total_exposure",
        ):
            _non_negative(getattr(self, field_name), field_name)
        _finite(self.realized_pnl, "realized_pnl")
        _finite(self.unrealized_pnl, "unrealized_pnl")
        _hash(self.strategy_configuration_hash, "strategy_configuration_hash")
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _utc(self.updated_at, "updated_at"))
        if self.updated_at < self.created_at:
            raise PaperTradingInvariantError("updated_at cannot precede created_at")
        if not _close(self.total_exposure, self.reserved_balance):
            raise PaperTradingInvariantError("total_exposure must equal reserved_balance")
        expected_equity = self.cash_balance + self.reserved_balance + self.unrealized_pnl
        if not _close(self.equity, expected_equity):
            raise PaperTradingInvariantError(
                "equity must equal cash, reserved capital and unrealized P&L"
            )

    def open_position(
        self,
        *,
        net_cost: Decimal,
        initial_mark_value: Decimal,
        occurred_at: datetime,
    ) -> PaperPortfolio:
        _positive(net_cost, "net_cost")
        _non_negative(initial_mark_value, "initial_mark_value")
        if self.status is not PaperPortfolioStatus.ACTIVE:
            raise PaperTradingInvariantError("portfolio is not active")
        if net_cost > self.cash_balance:
            raise PaperTradingInvariantError("portfolio has insufficient cash")
        cash = _amount(self.cash_balance - net_cost)
        reserved = _amount(self.reserved_balance + net_cost)
        unrealized = _amount(self.unrealized_pnl + initial_mark_value - net_cost)
        return replace(
            self,
            cash_balance=cash,
            reserved_balance=reserved,
            unrealized_pnl=unrealized,
            equity=cash + reserved + unrealized,
            total_exposure=reserved,
            updated_at=_utc(occurred_at, "occurred_at"),
        )

    def update_mark(
        self,
        *,
        previous_unrealized_pnl: Decimal,
        current_unrealized_pnl: Decimal,
        occurred_at: datetime,
    ) -> PaperPortfolio:
        _finite(previous_unrealized_pnl, "previous_unrealized_pnl")
        _finite(current_unrealized_pnl, "current_unrealized_pnl")
        unrealized = _amount(
            self.unrealized_pnl
            - _amount(previous_unrealized_pnl)
            + _amount(current_unrealized_pnl)
        )
        return replace(
            self,
            unrealized_pnl=unrealized,
            equity=self.cash_balance + self.reserved_balance + unrealized,
            updated_at=_utc(occurred_at, "occurred_at"),
        )

    def revalue_open_positions(
        self,
        *,
        unrealized_pnl: Decimal,
        occurred_at: datetime,
    ) -> PaperPortfolio:
        """Rebuild the materialized mark projection from durable positions."""
        _finite(unrealized_pnl, "unrealized_pnl")
        normalized = _amount(unrealized_pnl)
        return replace(
            self,
            unrealized_pnl=normalized,
            equity=_amount(self.cash_balance + self.reserved_balance + normalized),
            updated_at=_utc(occurred_at, "occurred_at"),
        )

    def settle_position(
        self,
        *,
        invested_amount: Decimal,
        previous_unrealized_pnl: Decimal,
        net_payout: Decimal,
        realized_pnl: Decimal,
        occurred_at: datetime,
    ) -> PaperPortfolio:
        _positive(invested_amount, "invested_amount")
        _finite(previous_unrealized_pnl, "previous_unrealized_pnl")
        _non_negative(net_payout, "net_payout")
        _finite(realized_pnl, "realized_pnl")
        if invested_amount > self.reserved_balance:
            raise PaperTradingInvariantError("settlement exceeds reserved capital")
        cash = _amount(self.cash_balance + net_payout)
        reserved = _amount(self.reserved_balance - invested_amount)
        unrealized = _amount(self.unrealized_pnl - _amount(previous_unrealized_pnl))
        return replace(
            self,
            cash_balance=cash,
            reserved_balance=reserved,
            realized_pnl=_amount(self.realized_pnl + _amount(realized_pnl)),
            unrealized_pnl=unrealized,
            equity=cash + reserved + unrealized,
            total_exposure=reserved,
            updated_at=_utc(occurred_at, "occurred_at"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TradeDecision:
    decision_id: UUID
    prediction_run_id: UUID
    portfolio_id: UUID
    decided_at: datetime
    decision: TradeDecisionType
    market_probability: Decimal | None
    system_probability: Decimal | None
    edge: Decimal | None
    confidence: Decimal
    opportunity_level: str
    proposed_stake: Decimal
    approved_stake: Decimal
    rejection_reasons: tuple[str, ...]
    risk_checks: tuple[str, ...]
    configuration_hash: str
    result_hash: str
    correlation_id: str
    causation_id: str | None
    experiment_run_id: UUID | None
    decision_source: TradeDecisionSource = TradeDecisionSource.AUTOMATIC
    override_reason: str | None = None
    idempotency_key: str | None = None
    side: PositionSide | None = None

    def __post_init__(self) -> None:
        for field_name in ("decision_id", "prediction_run_id", "portfolio_id"):
            _uuid(getattr(self, field_name), field_name)
        object.__setattr__(self, "decided_at", _utc(self.decided_at, "decided_at"))
        for field_name in ("market_probability", "system_probability"):
            value = getattr(self, field_name)
            if value is not None:
                _probability(value, field_name)
        if self.edge is not None:
            _edge(self.edge, "edge")
        _probability(self.confidence, "confidence")
        _non_negative(self.proposed_stake, "proposed_stake")
        _non_negative(self.approved_stake, "approved_stake")
        _text(self.opportunity_level, "opportunity_level")
        _hash(self.configuration_hash, "configuration_hash")
        _hash(self.result_hash, "result_hash")
        _text(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            _text(self.causation_id, "causation_id")
        if self.decision_source is TradeDecisionSource.MANUAL_OVERRIDE:
            if self.override_reason is None or self.idempotency_key is None or self.side is None:
                raise PaperTradingInvariantError(
                    "manual overrides require side, reason and idempotency key"
                )
            _text(self.override_reason, "override_reason")
            _text(self.idempotency_key, "idempotency_key")
        elif self.override_reason is not None or self.idempotency_key is not None:
            raise PaperTradingInvariantError(
                "automatic decisions cannot contain manual override metadata"
            )
        if self.decision is TradeDecisionType.BUY_YES and self.side is not PositionSide.YES:
            raise PaperTradingInvariantError("buy_yes decisions require YES side")
        if self.decision is TradeDecisionType.BUY_NO and self.side is not PositionSide.NO:
            raise PaperTradingInvariantError("buy_no decisions require NO side")
        if self.decision in {
            TradeDecisionType.ABSTAIN,
            TradeDecisionType.REJECTED,
        }:
            if self.approved_stake != 0:
                raise PaperTradingInvariantError("non-approved decisions cannot approve stake")
            if not self.rejection_reasons:
                raise PaperTradingInvariantError(
                    "non-approved decisions require an explicit reason"
                )
        elif self.approved_stake <= 0:
            raise PaperTradingInvariantError("approved decisions require stake")
        if self.approved_stake > self.proposed_stake:
            raise PaperTradingInvariantError("approved stake cannot exceed proposed stake")


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperOrder:
    order_id: UUID
    decision_id: UUID
    portfolio_id: UUID
    prediction_run_id: UUID
    market_id: UUID
    side: PositionSide
    requested_at: datetime
    requested_stake: Decimal
    status: PaperOrderStatus
    rejection_reason: str | None
    configuration_hash: str

    def __post_init__(self) -> None:
        for field_name in (
            "order_id",
            "decision_id",
            "portfolio_id",
            "prediction_run_id",
            "market_id",
        ):
            _uuid(getattr(self, field_name), field_name)
        object.__setattr__(self, "requested_at", _utc(self.requested_at, "requested_at"))
        _non_negative(self.requested_stake, "requested_stake")
        _hash(self.configuration_hash, "configuration_hash")
        if self.status is PaperOrderStatus.REJECTED:
            if self.rejection_reason is None:
                raise PaperTradingInvariantError("rejected orders require a rejection reason")
        elif self.rejection_reason is not None:
            raise PaperTradingInvariantError("only rejected orders can contain a rejection reason")
        if self.status in {PaperOrderStatus.PENDING, PaperOrderStatus.FILLED}:
            _positive(self.requested_stake, "requested_stake")


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperTrade:
    trade_id: UUID
    order_id: UUID
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

    def __post_init__(self) -> None:
        _uuid(self.trade_id, "trade_id")
        _uuid(self.order_id, "order_id")
        object.__setattr__(self, "executed_at", _utc(self.executed_at, "executed_at"))
        _probability(self.entry_probability, "entry_probability")
        _probability(self.effective_probability, "effective_probability")
        for field_name in (
            "units",
            "gross_cost",
            "net_cost",
            "maximum_loss",
            "potential_payout",
        ):
            _positive(getattr(self, field_name), field_name)
        _non_negative(self.fees, "fees")
        _non_negative(self.slippage_cost, "slippage_cost")
        _text(self.execution_model, "execution_model")
        _hash(self.result_hash, "result_hash")
        if self.effective_probability < self.entry_probability:
            raise PaperTradingInvariantError(
                "buy-side effective probability cannot improve through slippage"
            )
        if not _close(
            self.net_cost,
            self.gross_cost + self.fees + self.slippage_cost,
        ):
            raise PaperTradingInvariantError("net_cost must equal gross cost plus simulated costs")
        if not _close(self.maximum_loss, self.net_cost):
            raise PaperTradingInvariantError("maximum loss must equal net cost")
        if not _close(self.potential_payout, self.units):
            raise PaperTradingInvariantError("binary-contract potential payout must equal units")


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPosition:
    position_id: UUID
    portfolio_id: UUID
    market_id: UUID
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
    settlement_outcome: str | None
    prediction_run_id: UUID
    trade_id: UUID
    opportunity_level: str
    entry_edge: Decimal
    entry_confidence: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "position_id",
            "portfolio_id",
            "market_id",
            "prediction_run_id",
            "trade_id",
        ):
            _uuid(getattr(self, field_name), field_name)
        object.__setattr__(self, "opened_at", _utc(self.opened_at, "opened_at"))
        if self.closed_at is not None:
            object.__setattr__(self, "closed_at", _utc(self.closed_at, "closed_at"))
            if self.closed_at < self.opened_at:
                raise PaperTradingInvariantError("closed_at cannot precede opened_at")
        _positive(self.units, "units")
        _probability(self.average_entry_probability, "average_entry_probability")
        _positive(self.invested_amount, "invested_amount")
        if self.current_mark_probability is not None:
            _probability(self.current_mark_probability, "current_mark_probability")
        _finite(self.unrealized_pnl, "unrealized_pnl")
        _finite(self.realized_pnl, "realized_pnl")
        _edge(self.entry_edge, "entry_edge")
        _probability(self.entry_confidence, "entry_confidence")
        _text(self.opportunity_level, "opportunity_level")
        if self.status is PaperPositionStatus.OPEN:
            if self.closed_at is not None or self.settlement_outcome is not None:
                raise PaperTradingInvariantError("open position cannot contain settlement fields")
        elif self.closed_at is None or self.settlement_outcome is None:
            raise PaperTradingInvariantError("terminal position requires settlement fields")

    def mark(self, *, probability: Decimal, marked_at: datetime) -> PaperPosition:
        del marked_at
        _probability(probability, "probability")
        if self.status is not PaperPositionStatus.OPEN:
            return self
        value = self.units * (
            probability if self.side is PositionSide.YES else Decimal("1") - probability
        )
        return replace(
            self,
            current_mark_probability=probability,
            unrealized_pnl=_amount(value - self.invested_amount),
        )

    def settle(
        self,
        *,
        outcome: str,
        closed_at: datetime,
        realized_pnl: Decimal,
        cancelled: bool,
    ) -> PaperPosition:
        if self.status is not PaperPositionStatus.OPEN:
            raise PaperTradingInvariantError("position is already terminal")
        _text(outcome, "outcome")
        _finite(realized_pnl, "realized_pnl")
        return replace(
            self,
            closed_at=_utc(closed_at, "closed_at"),
            status=(PaperPositionStatus.CANCELLED if cancelled else PaperPositionStatus.SETTLED),
            current_mark_probability=None,
            unrealized_pnl=Decimal("0"),
            realized_pnl=realized_pnl,
            settlement_outcome=outcome,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperSettlement:
    settlement_id: UUID
    position_id: UUID
    market_id: UUID
    resolved_at: datetime
    outcome: str
    gross_payout: Decimal
    fees: Decimal
    net_payout: Decimal
    realized_pnl: Decimal
    settlement_policy: str
    result_hash: str
    created_at: datetime
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        for field_name in ("settlement_id", "position_id", "market_id"):
            _uuid(getattr(self, field_name), field_name)
        object.__setattr__(self, "resolved_at", _utc(self.resolved_at, "resolved_at"))
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        _text(self.outcome, "outcome")
        _non_negative(self.gross_payout, "gross_payout")
        _non_negative(self.fees, "fees")
        _non_negative(self.net_payout, "net_payout")
        _finite(self.realized_pnl, "realized_pnl")
        _text(self.settlement_policy, "settlement_policy")
        _hash(self.result_hash, "result_hash")
        _text(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            _text(self.causation_id, "causation_id")
        if self.created_at < self.resolved_at:
            raise PaperTradingInvariantError(
                "settlement cannot be created before official resolution"
            )
        if not _close(self.net_payout, self.gross_payout - self.fees):
            raise PaperTradingInvariantError(
                "net payout must equal gross payout minus settlement fees"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperLedgerEntry:
    ledger_entry_id: UUID
    portfolio_id: UUID
    entry_type: LedgerEntryType
    occurred_at: datetime
    amount: Decimal
    cash_balance_after: Decimal
    reserved_balance_after: Decimal
    equity_after: Decimal
    reference_type: str
    reference_id: UUID
    result_hash: str

    def __post_init__(self) -> None:
        _uuid(self.ledger_entry_id, "ledger_entry_id")
        _uuid(self.portfolio_id, "portfolio_id")
        _uuid(self.reference_id, "reference_id")
        object.__setattr__(self, "occurred_at", _utc(self.occurred_at, "occurred_at"))
        _finite(self.amount, "amount")
        for field_name in (
            "cash_balance_after",
            "reserved_balance_after",
            "equity_after",
        ):
            _non_negative(getattr(self, field_name), field_name)
        _text(self.reference_type, "reference_type")
        _hash(self.result_hash, "result_hash")


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPerformanceSnapshot:
    snapshot_id: UUID
    portfolio_id: UUID
    recorded_at: datetime
    cash_balance: Decimal
    reserved_balance: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    total_exposure: Decimal
    cumulative_costs: Decimal
    drawdown: Decimal
    open_positions: int
    closed_positions: int
    configuration_hash: str
    result_hash: str

    def __post_init__(self) -> None:
        _uuid(self.snapshot_id, "snapshot_id")
        _uuid(self.portfolio_id, "portfolio_id")
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at, "recorded_at"))
        for field_name in (
            "cash_balance",
            "reserved_balance",
            "equity",
            "total_exposure",
            "cumulative_costs",
            "drawdown",
        ):
            _non_negative(getattr(self, field_name), field_name)
        _finite(self.realized_pnl, "realized_pnl")
        _finite(self.unrealized_pnl, "unrealized_pnl")
        if self.open_positions < 0 or self.closed_positions < 0:
            raise PaperTradingInvariantError("position counts cannot be negative")
        _hash(self.configuration_hash, "configuration_hash")
        _hash(self.result_hash, "result_hash")


def _uuid(value: UUID, field_name: str) -> None:
    if not isinstance(value, UUID) or value.int == 0:
        raise PaperTradingInvariantError(f"{field_name} must be a non-zero UUID")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PaperTradingInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _text(value: str, field_name: str) -> None:
    if not value.strip():
        raise PaperTradingInvariantError(f"{field_name} cannot be blank")


def _finite(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PaperTradingInvariantError(f"{field_name} must be a finite Decimal")


def _amount(value: Decimal) -> Decimal:
    _finite(value, "amount")
    return value.quantize(_AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


def _non_negative(value: Decimal, field_name: str) -> None:
    _finite(value, field_name)
    if value < 0:
        raise PaperTradingInvariantError(f"{field_name} cannot be negative")


def _positive(value: Decimal, field_name: str) -> None:
    _finite(value, field_name)
    if value <= 0:
        raise PaperTradingInvariantError(f"{field_name} must be positive")


def _probability(value: Decimal, field_name: str) -> None:
    _finite(value, field_name)
    if not Decimal("0") <= value <= Decimal("1"):
        raise PaperTradingInvariantError(f"{field_name} must be between 0 and 1")


def _edge(value: Decimal, field_name: str) -> None:
    _finite(value, field_name)
    if not Decimal("-1") <= value <= Decimal("1"):
        raise PaperTradingInvariantError(f"{field_name} must be between -1 and 1")


def _hash(value: str, field_name: str) -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise PaperTradingInvariantError(f"{field_name} must be a SHA-256 digest")


def _close(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= _TOLERANCE
