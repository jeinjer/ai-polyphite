"""Add deterministic paper trading portfolios and audit records.

Revision ID: 20260728_0008
Revises: 20260728_0007
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0008"
down_revision: str | Sequence[str] | None = "20260728_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_portfolios",
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("currency_unit", sa.String(32), nullable=False),
        sa.Column("initial_balance", sa.Numeric(28, 8), nullable=False),
        sa.Column("cash_balance", sa.Numeric(28, 8), nullable=False),
        sa.Column("reserved_balance", sa.Numeric(28, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("equity", sa.Numeric(28, 8), nullable=False),
        sa.Column("total_exposure", sa.Numeric(28, 8), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("strategy_configuration_hash", sa.String(64), nullable=False),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "currency_unit IN ('USD_SIMULATED', 'MANA_SIMULATED')",
            name="paper_portfolios_valid_currency",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'closed')",
            name="paper_portfolios_valid_status",
        ),
        sa.CheckConstraint(
            "initial_balance > 0",
            name="paper_portfolios_initial_positive",
        ),
        sa.CheckConstraint(
            "cash_balance >= 0 AND reserved_balance >= 0 "
            "AND equity >= 0 AND total_exposure >= 0",
            name="paper_portfolios_balances_non_negative",
        ),
        sa.CheckConstraint(
            "total_exposure = reserved_balance",
            name="paper_portfolios_exposure_matches_reserve",
        ),
        sa.CheckConstraint(
            "equity = cash_balance + reserved_balance + unrealized_pnl",
            name="paper_portfolios_equity_coherent",
        ),
        sa.CheckConstraint(
            "char_length(name) > 0",
            name="paper_portfolios_name_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["experiment_runs.experiment_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("portfolio_id"),
        sa.UniqueConstraint(
            "experiment_run_id",
            "strategy_configuration_hash",
            name="uq_paper_portfolios_experiment_strategy",
        ),
    )
    op.create_index(
        "ix_paper_portfolios_experiment_status",
        "paper_portfolios",
        ["experiment_run_id", "status"],
    )
    op.create_index(
        op.f("ix_paper_portfolios_status"),
        "paper_portfolios",
        ["status"],
    )

    op.create_table(
        "trade_decisions",
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=True),
        sa.Column("market_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("system_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("edge", sa.Numeric(12, 10), nullable=True),
        sa.Column("confidence", sa.Numeric(12, 10), nullable=False),
        sa.Column("opportunity_level", sa.String(32), nullable=False),
        sa.Column("proposed_stake", sa.Numeric(28, 8), nullable=False),
        sa.Column("approved_stake", sa.Numeric(28, 8), nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=False),
        sa.Column("risk_checks", sa.JSON(), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(200), nullable=False),
        sa.Column("causation_id", sa.String(200), nullable=True),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('buy_yes', 'buy_no', 'abstain', 'rejected')",
            name="trade_decisions_valid_decision",
        ),
        sa.CheckConstraint(
            "side IS NULL OR side IN ('yes', 'no')",
            name="trade_decisions_valid_side",
        ),
        sa.CheckConstraint(
            "market_probability IS NULL OR "
            "(market_probability >= 0 AND market_probability <= 1)",
            name="trade_decisions_market_probability_range",
        ),
        sa.CheckConstraint(
            "system_probability IS NULL OR "
            "(system_probability >= 0 AND system_probability <= 1)",
            name="trade_decisions_system_probability_range",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="trade_decisions_confidence_range",
        ),
        sa.CheckConstraint(
            "proposed_stake >= 0 AND approved_stake >= 0 "
            "AND approved_stake <= proposed_stake",
            name="trade_decisions_stakes_coherent",
        ),
        sa.CheckConstraint(
            "(decision IN ('buy_yes', 'buy_no') AND approved_stake > 0 "
            "AND side IS NOT NULL) OR "
            "(decision IN ('abstain', 'rejected') AND approved_stake = 0)",
            name="trade_decisions_terminal_state",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["experiment_runs.experiment_run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_run_id"],
            ["prediction_runs.prediction_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("decision_id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "prediction_run_id",
            name="uq_trade_decisions_portfolio_prediction",
        ),
    )
    for column in ("decision", "side", "opportunity_level"):
        op.create_index(
            op.f(f"ix_trade_decisions_{column}"),
            "trade_decisions",
            [column],
        )
    op.create_index(
        "ix_trade_decisions_portfolio_decided_at",
        "trade_decisions",
        ["portfolio_id", "decided_at"],
    )
    op.create_index(
        "ix_trade_decisions_experiment_decided_at",
        "trade_decisions",
        ["experiment_run_id", "decided_at"],
    )

    op.create_table(
        "paper_orders",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_stake", sa.Numeric(28, 8), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "side IN ('yes', 'no')",
            name="paper_orders_valid_side",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'filled', 'rejected', 'cancelled')",
            name="paper_orders_valid_status",
        ),
        sa.CheckConstraint(
            "requested_stake >= 0",
            name="paper_orders_stake_non_negative",
        ),
        sa.CheckConstraint(
            "(status = 'rejected' AND rejection_reason IS NOT NULL) OR "
            "(status <> 'rejected' AND rejection_reason IS NULL)",
            name="paper_orders_rejection_coherent",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["trade_decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_run_id"],
            ["prediction_runs.prediction_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("order_id"),
        sa.UniqueConstraint("decision_id", name="uq_paper_orders_decision"),
    )
    op.create_index(
        op.f("ix_paper_orders_status"),
        "paper_orders",
        ["status"],
    )
    op.create_index(
        "ix_paper_orders_portfolio_requested_at",
        "paper_orders",
        ["portfolio_id", "requested_at"],
    )

    op.create_table(
        "paper_trades",
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("entry_probability", sa.Numeric(12, 10), nullable=False),
        sa.Column("effective_probability", sa.Numeric(12, 10), nullable=False),
        sa.Column("units", sa.Numeric(28, 8), nullable=False),
        sa.Column("gross_cost", sa.Numeric(28, 8), nullable=False),
        sa.Column("fees", sa.Numeric(28, 8), nullable=False),
        sa.Column("slippage_cost", sa.Numeric(28, 8), nullable=False),
        sa.Column("net_cost", sa.Numeric(28, 8), nullable=False),
        sa.Column("maximum_loss", sa.Numeric(28, 8), nullable=False),
        sa.Column("potential_payout", sa.Numeric(28, 8), nullable=False),
        sa.Column("execution_model", sa.String(100), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "side IN ('yes', 'no')",
            name="paper_trades_valid_side",
        ),
        sa.CheckConstraint(
            "entry_probability > 0 AND entry_probability < 1 "
            "AND effective_probability > 0 AND effective_probability < 1",
            name="paper_trades_probability_range",
        ),
        sa.CheckConstraint(
            "effective_probability >= entry_probability",
            name="paper_trades_adverse_slippage",
        ),
        sa.CheckConstraint(
            "units > 0 AND gross_cost > 0 AND fees >= 0 "
            "AND slippage_cost >= 0 AND net_cost > 0 "
            "AND maximum_loss > 0 AND potential_payout > 0",
            name="paper_trades_amounts_valid",
        ),
        sa.CheckConstraint(
            "net_cost = gross_cost + fees + slippage_cost",
            name="paper_trades_net_cost_coherent",
        ),
        sa.CheckConstraint(
            "maximum_loss = net_cost",
            name="paper_trades_maximum_loss_coherent",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["paper_orders.order_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("trade_id"),
        sa.UniqueConstraint("order_id", name="uq_paper_trades_order"),
    )
    op.create_index(
        "ix_paper_trades_executed_at",
        "paper_trades",
        ["executed_at"],
    )

    op.create_table(
        "paper_positions",
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("units", sa.Numeric(28, 8), nullable=False),
        sa.Column("average_entry_probability", sa.Numeric(12, 10), nullable=False),
        sa.Column("invested_amount", sa.Numeric(28, 8), nullable=False),
        sa.Column("current_mark_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("settlement_outcome", sa.String(32), nullable=True),
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_level", sa.String(32), nullable=False),
        sa.Column("entry_edge", sa.Numeric(12, 10), nullable=False),
        sa.Column("entry_confidence", sa.Numeric(12, 10), nullable=False),
        sa.CheckConstraint(
            "side IN ('yes', 'no')",
            name="paper_positions_valid_side",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'settled', 'cancelled')",
            name="paper_positions_valid_status",
        ),
        sa.CheckConstraint(
            "units > 0 AND invested_amount > 0",
            name="paper_positions_amounts_positive",
        ),
        sa.CheckConstraint(
            "average_entry_probability > 0 AND average_entry_probability < 1",
            name="paper_positions_entry_probability_range",
        ),
        sa.CheckConstraint(
            "current_mark_probability IS NULL OR "
            "(current_mark_probability >= 0 AND current_mark_probability <= 1)",
            name="paper_positions_mark_probability_range",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND closed_at IS NULL "
            "AND settlement_outcome IS NULL) OR "
            "(status IN ('settled', 'cancelled') AND closed_at IS NOT NULL "
            "AND settlement_outcome IS NOT NULL)",
            name="paper_positions_terminal_state",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_run_id"],
            ["prediction_runs.prediction_run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["paper_trades.trade_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("position_id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "market_id",
            name="uq_paper_positions_portfolio_market",
        ),
        sa.UniqueConstraint("trade_id", name="uq_paper_positions_trade"),
    )
    for column in ("category", "status", "settlement_outcome"):
        op.create_index(
            op.f(f"ix_paper_positions_{column}"),
            "paper_positions",
            [column],
        )
    op.create_index(
        "ix_paper_positions_portfolio_status",
        "paper_positions",
        ["portfolio_id", "status"],
    )

    op.create_table(
        "paper_settlements",
        sa.Column("settlement_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("gross_payout", sa.Numeric(28, 8), nullable=False),
        sa.Column("fees", sa.Numeric(28, 8), nullable=False),
        sa.Column("net_payout", sa.Numeric(28, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("settlement_policy", sa.String(100), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(200), nullable=False),
        sa.Column("causation_id", sa.String(200), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('yes', 'no', 'cancelled')",
            name="paper_settlements_valid_outcome",
        ),
        sa.CheckConstraint(
            "gross_payout >= 0 AND fees >= 0 AND net_payout >= 0",
            name="paper_settlements_amounts_non_negative",
        ),
        sa.CheckConstraint(
            "net_payout = gross_payout - fees",
            name="paper_settlements_net_payout_coherent",
        ),
        sa.CheckConstraint(
            "created_at >= resolved_at",
            name="paper_settlements_after_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.position_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("settlement_id"),
        sa.UniqueConstraint("position_id", name="uq_paper_settlements_position"),
    )
    op.create_index(
        op.f("ix_paper_settlements_outcome"),
        "paper_settlements",
        ["outcome"],
    )
    op.create_index(
        "ix_paper_settlements_market_resolved_at",
        "paper_settlements",
        ["market_id", "resolved_at"],
    )

    op.create_table(
        "paper_ledger_entries",
        sa.Column("ledger_entry_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(28, 8), nullable=False),
        sa.Column("cash_balance_after", sa.Numeric(28, 8), nullable=False),
        sa.Column("reserved_balance_after", sa.Numeric(28, 8), nullable=False),
        sa.Column("equity_after", sa.Numeric(28, 8), nullable=False),
        sa.Column("reference_type", sa.String(64), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('initial_capital', 'position_opened', "
            "'settlement', 'cancellation_refund')",
            name="paper_ledger_entries_valid_type",
        ),
        sa.CheckConstraint(
            "cash_balance_after >= 0 AND reserved_balance_after >= 0 "
            "AND equity_after >= 0",
            name="paper_ledger_entries_balances_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("ledger_entry_id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "reference_type",
            "reference_id",
            name="uq_paper_ledger_entries_reference",
        ),
    )
    op.create_index(
        "ix_paper_ledger_entries_portfolio_occurred_at",
        "paper_ledger_entries",
        ["portfolio_id", "occurred_at"],
    )

    op.create_table(
        "paper_performance_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash_balance", sa.Numeric(28, 8), nullable=False),
        sa.Column("reserved_balance", sa.Numeric(28, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(28, 8), nullable=False),
        sa.Column("equity", sa.Numeric(28, 8), nullable=False),
        sa.Column("total_exposure", sa.Numeric(28, 8), nullable=False),
        sa.Column("cumulative_costs", sa.Numeric(28, 8), nullable=False),
        sa.Column("drawdown", sa.Numeric(12, 10), nullable=False),
        sa.Column("open_positions", sa.Integer(), nullable=False),
        sa.Column("closed_positions", sa.Integer(), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "cash_balance >= 0 AND reserved_balance >= 0 AND equity >= 0 "
            "AND total_exposure >= 0 AND cumulative_costs >= 0 "
            "AND drawdown >= 0 AND drawdown <= 1",
            name="paper_performance_snapshots_values_valid",
        ),
        sa.CheckConstraint(
            "open_positions >= 0 AND closed_positions >= 0",
            name="paper_performance_snapshots_counts_valid",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "recorded_at",
            name="uq_paper_performance_snapshots_portfolio_time",
        ),
    )
    op.create_index(
        "ix_paper_performance_snapshots_portfolio_recorded_at",
        "paper_performance_snapshots",
        ["portfolio_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_performance_snapshots_portfolio_recorded_at",
        table_name="paper_performance_snapshots",
    )
    op.drop_table("paper_performance_snapshots")
    op.drop_index(
        "ix_paper_ledger_entries_portfolio_occurred_at",
        table_name="paper_ledger_entries",
    )
    op.drop_table("paper_ledger_entries")
    op.drop_index(
        "ix_paper_settlements_market_resolved_at",
        table_name="paper_settlements",
    )
    op.drop_index(
        op.f("ix_paper_settlements_outcome"),
        table_name="paper_settlements",
    )
    op.drop_table("paper_settlements")
    op.drop_index(
        "ix_paper_positions_portfolio_status",
        table_name="paper_positions",
    )
    for column in ("settlement_outcome", "status", "category"):
        op.drop_index(
            op.f(f"ix_paper_positions_{column}"),
            table_name="paper_positions",
        )
    op.drop_table("paper_positions")
    op.drop_index("ix_paper_trades_executed_at", table_name="paper_trades")
    op.drop_table("paper_trades")
    op.drop_index(
        "ix_paper_orders_portfolio_requested_at",
        table_name="paper_orders",
    )
    op.drop_index(op.f("ix_paper_orders_status"), table_name="paper_orders")
    op.drop_table("paper_orders")
    op.drop_index(
        "ix_trade_decisions_experiment_decided_at",
        table_name="trade_decisions",
    )
    op.drop_index(
        "ix_trade_decisions_portfolio_decided_at",
        table_name="trade_decisions",
    )
    for column in ("opportunity_level", "side", "decision"):
        op.drop_index(
            op.f(f"ix_trade_decisions_{column}"),
            table_name="trade_decisions",
        )
    op.drop_table("trade_decisions")
    op.drop_index(
        op.f("ix_paper_portfolios_status"),
        table_name="paper_portfolios",
    )
    op.drop_index(
        "ix_paper_portfolios_experiment_status",
        table_name="paper_portfolios",
    )
    op.drop_table("paper_portfolios")
