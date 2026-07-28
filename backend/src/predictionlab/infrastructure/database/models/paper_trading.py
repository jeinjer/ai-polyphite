"""Durable models for simulated portfolios and append-only audit records."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base
from predictionlab.infrastructure.database.models.markets import (
    AMOUNT_PRECISION,
    AMOUNT_SCALE,
    PROBABILITY_PRECISION,
    PROBABILITY_SCALE,
)


class PaperPortfolioModel(Base):
    __tablename__ = "paper_portfolios"
    __table_args__ = (
        CheckConstraint(
            "currency_unit IN ('USD_SIMULATED', 'MANA_SIMULATED')",
            name="paper_portfolios_valid_currency",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'closed')",
            name="paper_portfolios_valid_status",
        ),
        CheckConstraint(
            "initial_balance > 0",
            name="paper_portfolios_initial_positive",
        ),
        CheckConstraint(
            "cash_balance >= 0 AND reserved_balance >= 0 "
            "AND equity >= 0 AND total_exposure >= 0",
            name="paper_portfolios_balances_non_negative",
        ),
        CheckConstraint(
            "total_exposure = reserved_balance",
            name="paper_portfolios_exposure_matches_reserve",
        ),
        CheckConstraint(
            "equity = cash_balance + reserved_balance + unrealized_pnl",
            name="paper_portfolios_equity_coherent",
        ),
        CheckConstraint(
            "char_length(name) > 0",
            name="paper_portfolios_name_not_blank",
        ),
        UniqueConstraint(
            "experiment_run_id",
            "strategy_configuration_hash",
            name="uq_paper_portfolios_experiment_strategy",
        ),
        Index(
            "ix_paper_portfolios_experiment_status",
            "experiment_run_id",
            "status",
        ),
    )

    portfolio_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    reserved_balance: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    equity: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    total_exposure: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strategy_configuration_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    experiment_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiment_runs.experiment_run_id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradeDecisionModel(Base):
    __tablename__ = "trade_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('buy_yes', 'buy_no', 'abstain', 'rejected')",
            name="trade_decisions_valid_decision",
        ),
        CheckConstraint(
            "side IS NULL OR side IN ('yes', 'no')",
            name="trade_decisions_valid_side",
        ),
        CheckConstraint(
            "market_probability IS NULL OR "
            "(market_probability >= 0 AND market_probability <= 1)",
            name="trade_decisions_market_probability_range",
        ),
        CheckConstraint(
            "system_probability IS NULL OR "
            "(system_probability >= 0 AND system_probability <= 1)",
            name="trade_decisions_system_probability_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="trade_decisions_confidence_range",
        ),
        CheckConstraint(
            "proposed_stake >= 0 AND approved_stake >= 0 "
            "AND approved_stake <= proposed_stake",
            name="trade_decisions_stakes_coherent",
        ),
        CheckConstraint(
            "(decision IN ('buy_yes', 'buy_no') AND approved_stake > 0 "
            "AND side IS NOT NULL) OR "
            "(decision IN ('abstain', 'rejected') AND approved_stake = 0)",
            name="trade_decisions_terminal_state",
        ),
        UniqueConstraint(
            "portfolio_id",
            "prediction_run_id",
            name="uq_trade_decisions_portfolio_prediction",
        ),
        Index(
            "ix_trade_decisions_portfolio_decided_at",
            "portfolio_id",
            "decided_at",
        ),
        Index(
            "ix_trade_decisions_experiment_decided_at",
            "experiment_run_id",
            "decided_at",
        ),
    )

    decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("prediction_runs.prediction_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str | None] = mapped_column(String(8), index=True)
    market_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    system_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    edge: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    opportunity_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    proposed_stake: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    approved_stake: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    rejection_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    risk_checks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(200))
    experiment_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiment_runs.experiment_run_id", ondelete="RESTRICT"),
    )


class PaperOrderModel(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (
        CheckConstraint(
            "side IN ('yes', 'no')",
            name="paper_orders_valid_side",
        ),
        CheckConstraint(
            "status IN ('pending', 'filled', 'rejected', 'cancelled')",
            name="paper_orders_valid_status",
        ),
        CheckConstraint(
            "requested_stake >= 0",
            name="paper_orders_stake_non_negative",
        ),
        CheckConstraint(
            "(status = 'rejected' AND rejection_reason IS NOT NULL) OR "
            "(status <> 'rejected' AND rejection_reason IS NULL)",
            name="paper_orders_rejection_coherent",
        ),
        UniqueConstraint("decision_id", name="uq_paper_orders_decision"),
        Index(
            "ix_paper_orders_portfolio_requested_at",
            "portfolio_id",
            "requested_at",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trade_decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("prediction_runs.prediction_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_stake: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PaperTradeModel(Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        CheckConstraint("side IN ('yes', 'no')", name="paper_trades_valid_side"),
        CheckConstraint(
            "entry_probability > 0 AND entry_probability < 1 "
            "AND effective_probability > 0 AND effective_probability < 1",
            name="paper_trades_probability_range",
        ),
        CheckConstraint(
            "effective_probability >= entry_probability",
            name="paper_trades_adverse_slippage",
        ),
        CheckConstraint(
            "units > 0 AND gross_cost > 0 AND fees >= 0 "
            "AND slippage_cost >= 0 AND net_cost > 0 "
            "AND maximum_loss > 0 AND potential_payout > 0",
            name="paper_trades_amounts_valid",
        ),
        CheckConstraint(
            "net_cost = gross_cost + fees + slippage_cost",
            name="paper_trades_net_cost_coherent",
        ),
        CheckConstraint(
            "maximum_loss = net_cost",
            name="paper_trades_maximum_loss_coherent",
        ),
        UniqueConstraint("order_id", name="uq_paper_trades_order"),
        Index("ix_paper_trades_executed_at", "executed_at"),
    )

    trade_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_orders.order_id", ondelete="RESTRICT"),
        nullable=False,
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    entry_probability: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    effective_probability: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    units: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    gross_cost: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    fees: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    slippage_cost: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    net_cost: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    maximum_loss: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    potential_payout: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    execution_model: Mapped[str] = mapped_column(String(100), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PaperPositionModel(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (
        CheckConstraint("side IN ('yes', 'no')", name="paper_positions_valid_side"),
        CheckConstraint(
            "status IN ('open', 'settled', 'cancelled')",
            name="paper_positions_valid_status",
        ),
        CheckConstraint(
            "units > 0 AND invested_amount > 0",
            name="paper_positions_amounts_positive",
        ),
        CheckConstraint(
            "average_entry_probability > 0 AND average_entry_probability < 1",
            name="paper_positions_entry_probability_range",
        ),
        CheckConstraint(
            "current_mark_probability IS NULL OR "
            "(current_mark_probability >= 0 AND current_mark_probability <= 1)",
            name="paper_positions_mark_probability_range",
        ),
        CheckConstraint(
            "(status = 'open' AND closed_at IS NULL "
            "AND settlement_outcome IS NULL) OR "
            "(status IN ('settled', 'cancelled') AND closed_at IS NOT NULL "
            "AND settlement_outcome IS NOT NULL)",
            name="paper_positions_terminal_state",
        ),
        UniqueConstraint(
            "portfolio_id",
            "market_id",
            name="uq_paper_positions_portfolio_market",
        ),
        UniqueConstraint("trade_id", name="uq_paper_positions_trade"),
        Index(
            "ix_paper_positions_portfolio_status",
            "portfolio_id",
            "status",
        ),
        Index("ix_paper_positions_category", "category"),
    )

    position_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(200))
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    units: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    average_entry_probability: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    invested_amount: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    current_mark_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    settlement_outcome: Mapped[str | None] = mapped_column(String(32), index=True)
    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("prediction_runs.prediction_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    trade_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_trades.trade_id", ondelete="RESTRICT"),
        nullable=False,
    )
    opportunity_level: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_edge: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    entry_confidence: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )


class PaperSettlementModel(Base):
    __tablename__ = "paper_settlements"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('yes', 'no', 'cancelled')",
            name="paper_settlements_valid_outcome",
        ),
        CheckConstraint(
            "gross_payout >= 0 AND fees >= 0 AND net_payout >= 0",
            name="paper_settlements_amounts_non_negative",
        ),
        CheckConstraint(
            "net_payout = gross_payout - fees",
            name="paper_settlements_net_payout_coherent",
        ),
        CheckConstraint(
            "created_at >= resolved_at",
            name="paper_settlements_after_resolution",
        ),
        UniqueConstraint("position_id", name="uq_paper_settlements_position"),
        Index("ix_paper_settlements_market_resolved_at", "market_id", "resolved_at"),
    )

    settlement_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    position_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_positions.position_id", ondelete="RESTRICT"),
        nullable=False,
    )
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    gross_payout: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    fees: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    net_payout: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    settlement_policy: Mapped[str] = mapped_column(String(100), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(200))


class PaperLedgerEntryModel(Base):
    __tablename__ = "paper_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('initial_capital', 'position_opened', "
            "'settlement', 'cancellation_refund')",
            name="paper_ledger_entries_valid_type",
        ),
        CheckConstraint(
            "cash_balance_after >= 0 AND reserved_balance_after >= 0 "
            "AND equity_after >= 0",
            name="paper_ledger_entries_balances_non_negative",
        ),
        UniqueConstraint(
            "portfolio_id",
            "reference_type",
            "reference_id",
            name="uq_paper_ledger_entries_reference",
        ),
        Index(
            "ix_paper_ledger_entries_portfolio_occurred_at",
            "portfolio_id",
            "occurred_at",
        ),
    )

    ledger_entry_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    cash_balance_after: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    reserved_balance_after: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    equity_after: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    reference_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class PaperPerformanceSnapshotModel(Base):
    __tablename__ = "paper_performance_snapshots"
    __table_args__ = (
        CheckConstraint(
            "cash_balance >= 0 AND reserved_balance >= 0 AND equity >= 0 "
            "AND total_exposure >= 0 AND cumulative_costs >= 0 "
            "AND drawdown >= 0 AND drawdown <= 1",
            name="paper_performance_snapshots_values_valid",
        ),
        CheckConstraint(
            "open_positions >= 0 AND closed_positions >= 0",
            name="paper_performance_snapshots_counts_valid",
        ),
        UniqueConstraint(
            "portfolio_id",
            "recorded_at",
            name="uq_paper_performance_snapshots_portfolio_time",
        ),
        Index(
            "ix_paper_performance_snapshots_portfolio_recorded_at",
            "portfolio_id",
            "recorded_at",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    reserved_balance: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    equity: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    total_exposure: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    cumulative_costs: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    drawdown: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    open_positions: Mapped[int] = mapped_column(nullable=False)
    closed_positions: Mapped[int] = mapped_column(nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
