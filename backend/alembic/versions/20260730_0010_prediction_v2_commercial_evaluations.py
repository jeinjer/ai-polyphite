"""Separate prediction outcomes from durable commercial evaluations.

Revision ID: 20260730_0010
Revises: 20260728_0009
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0010"
down_revision: str | Sequence[str] | None = "20260728_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prediction_runs",
        sa.Column("estimated_outcome", sa.String(32), nullable=True),
    )
    op.drop_constraint(
        "prediction_runs_valid_status",
        "prediction_runs",
        type_="check",
    )
    op.drop_constraint(
        "prediction_runs_valid_terminal_state",
        "prediction_runs",
        type_="check",
    )
    op.create_check_constraint(
        "prediction_runs_valid_status",
        "prediction_runs",
        "status IN ('predicted', 'completed', 'abstained', 'failed')",
    )
    op.create_check_constraint(
        "prediction_runs_valid_estimated_outcome",
        "prediction_runs",
        "estimated_outcome IS NULL OR estimated_outcome IN ('yes', 'no')",
    )
    op.create_check_constraint(
        "prediction_runs_valid_terminal_state",
        "prediction_runs",
        "(status IN ('predicted', 'completed') "
        "AND recommendation IN ('yes', 'no') "
        "AND consensus_probability IS NOT NULL AND edge IS NOT NULL "
        "AND safe_error_type IS NULL AND abstention_reason IS NULL "
        "AND (status = 'completed' OR estimated_outcome IS NOT NULL)) OR "
        "(status = 'abstained' AND recommendation = 'abstain' "
        "AND consensus_probability IS NULL AND edge IS NULL "
        "AND safe_error_type IS NULL AND abstention_reason IS NOT NULL) OR "
        "(status = 'failed' AND safe_error_type IS NOT NULL "
        "AND abstention_reason IS NULL)",
    )
    op.create_index(
        "ix_prediction_runs_estimated_outcome",
        "prediction_runs",
        ["estimated_outcome"],
    )
    op.add_column(
        "trade_decisions",
        sa.Column(
            "decision_source",
            sa.String(32),
            nullable=False,
            server_default="automatic",
        ),
    )
    op.add_column(
        "trade_decisions",
        sa.Column("override_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "trade_decisions",
        sa.Column("idempotency_key", sa.String(200), nullable=True),
    )
    op.create_check_constraint(
        "trade_decisions_valid_source",
        "trade_decisions",
        "decision_source IN ('automatic', 'manual_override')",
    )
    op.create_check_constraint(
        "trade_decisions_override_metadata_coherent",
        "trade_decisions",
        "(decision_source = 'manual_override' "
        "AND override_reason IS NOT NULL AND idempotency_key IS NOT NULL) "
        "OR (decision_source = 'automatic' "
        "AND override_reason IS NULL AND idempotency_key IS NULL)",
    )
    op.create_index(
        "uq_trade_decisions_portfolio_idempotency",
        "trade_decisions",
        ["portfolio_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "commercial_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.String(160), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_outcome", sa.String(8), nullable=True),
        sa.Column("potential_side", sa.String(16), nullable=False),
        sa.Column("market_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("consensus_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("gross_edge", sa.Numeric(12, 10), nullable=True),
        sa.Column("estimated_fees", sa.Numeric(12, 10), nullable=False),
        sa.Column("estimated_slippage", sa.Numeric(12, 10), nullable=False),
        sa.Column("estimated_other_costs", sa.Numeric(12, 10), nullable=False),
        sa.Column("net_edge", sa.Numeric(12, 10), nullable=True),
        sa.Column("confidence", sa.Numeric(12, 10), nullable=False),
        sa.Column("commercial_label", sa.String(32), nullable=False),
        sa.Column("is_actionable", sa.Boolean(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("portfolio_has_open_position", sa.Boolean(), nullable=False),
        sa.Column("data_freshness_status", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "estimated_outcome IS NULL OR estimated_outcome IN ('yes', 'no')",
            name="commercial_evaluations_valid_estimated_outcome",
        ),
        sa.CheckConstraint(
            "potential_side IN ('buy_yes', 'buy_no', 'none')",
            name="commercial_evaluations_valid_potential_side",
        ),
        sa.CheckConstraint(
            "commercial_label IN "
            "('actionable', 'not_actionable', 'not_evaluable')",
            name="commercial_evaluations_valid_label",
        ),
        sa.CheckConstraint(
            "data_freshness_status IN ('fresh', 'stale', 'unavailable')",
            name="commercial_evaluations_valid_freshness",
        ),
        sa.CheckConstraint(
            "market_probability IS NULL OR "
            "(market_probability >= 0 AND market_probability <= 1)",
            name="commercial_evaluations_market_probability_range",
        ),
        sa.CheckConstraint(
            "consensus_probability IS NULL OR "
            "(consensus_probability >= 0 AND consensus_probability <= 1)",
            name="commercial_evaluations_consensus_probability_range",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="commercial_evaluations_confidence_range",
        ),
        sa.CheckConstraint(
            "gross_edge IS NULL OR (gross_edge >= -1 AND gross_edge <= 1)",
            name="commercial_evaluations_gross_edge_range",
        ),
        sa.CheckConstraint(
            "net_edge IS NULL OR (net_edge >= -1 AND net_edge <= 1)",
            name="commercial_evaluations_net_edge_range",
        ),
        sa.CheckConstraint(
            "estimated_fees >= 0 AND estimated_fees <= 1 "
            "AND estimated_slippage >= 0 AND estimated_slippage <= 1 "
            "AND estimated_other_costs >= 0 AND estimated_other_costs <= 1",
            name="commercial_evaluations_cost_range",
        ),
        sa.CheckConstraint(
            "(commercial_label = 'actionable' AND is_actionable) OR "
            "(commercial_label <> 'actionable' AND NOT is_actionable)",
            name="commercial_evaluations_actionable_coherent",
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
        sa.PrimaryKeyConstraint("evaluation_id"),
        sa.UniqueConstraint(
            "prediction_run_id",
            "portfolio_id",
            "campaign_id",
            "configuration_hash",
            name="uq_commercial_evaluations_scope",
        ),
    )
    op.create_index(
        "uq_commercial_evaluations_scope_without_portfolio",
        "commercial_evaluations",
        ["prediction_run_id", "campaign_id", "configuration_hash"],
        unique=True,
        postgresql_where=sa.text("portfolio_id IS NULL"),
    )
    op.create_index(
        "ix_commercial_evaluations_campaign_evaluated_at",
        "commercial_evaluations",
        ["campaign_id", "evaluated_at"],
    )
    op.create_index(
        "ix_commercial_evaluations_label_evaluated_at",
        "commercial_evaluations",
        ["commercial_label", "evaluated_at"],
    )
    op.create_index(
        "ix_commercial_evaluations_portfolio_evaluated_at",
        "commercial_evaluations",
        ["portfolio_id", "evaluated_at"],
    )


def downgrade() -> None:
    op.drop_table("commercial_evaluations")
    op.drop_index(
        "uq_trade_decisions_portfolio_idempotency",
        table_name="trade_decisions",
    )
    op.drop_constraint(
        "trade_decisions_override_metadata_coherent",
        "trade_decisions",
        type_="check",
    )
    op.drop_constraint(
        "trade_decisions_valid_source",
        "trade_decisions",
        type_="check",
    )
    op.drop_column("trade_decisions", "idempotency_key")
    op.drop_column("trade_decisions", "override_reason")
    op.drop_column("trade_decisions", "decision_source")
    op.drop_index(
        "ix_prediction_runs_estimated_outcome",
        table_name="prediction_runs",
    )
    op.drop_constraint(
        "prediction_runs_valid_terminal_state",
        "prediction_runs",
        type_="check",
    )
    op.drop_constraint(
        "prediction_runs_valid_estimated_outcome",
        "prediction_runs",
        type_="check",
    )
    op.drop_constraint(
        "prediction_runs_valid_status",
        "prediction_runs",
        type_="check",
    )
    op.execute(
        "UPDATE prediction_runs SET status = 'completed' "
        "WHERE status = 'predicted'"
    )
    op.create_check_constraint(
        "prediction_runs_valid_status",
        "prediction_runs",
        "status IN ('completed', 'abstained', 'failed')",
    )
    op.create_check_constraint(
        "prediction_runs_valid_terminal_state",
        "prediction_runs",
        "(status = 'completed' AND recommendation IN ('yes', 'no') "
        "AND consensus_probability IS NOT NULL AND edge IS NOT NULL "
        "AND safe_error_type IS NULL AND abstention_reason IS NULL) OR "
        "(status = 'abstained' AND recommendation = 'abstain' "
        "AND consensus_probability IS NULL AND edge IS NULL "
        "AND safe_error_type IS NULL AND abstention_reason IS NOT NULL) OR "
        "(status = 'failed' AND safe_error_type IS NOT NULL "
        "AND abstention_reason IS NULL)",
    )
    op.drop_column("prediction_runs", "estimated_outcome")
