"""Add durable continuous paper validation audit records.

Revision ID: 20260728_0009
Revises: 20260728_0008
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0009"
down_revision: str | Sequence[str] | None = "20260728_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_validation_runs",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_key", sa.String(64), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=True),
        sa.Column("prediction_count", sa.Integer(), nullable=False),
        sa.Column("decision_count", sa.Integer(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("settlement_count", sa.Integer(), nullable=False),
        sa.Column("reconciliation_ok", sa.Boolean(), nullable=True),
        sa.Column("reconciliation_details", sa.JSON(), nullable=True),
        sa.Column("reconciliation_result_hash", sa.String(64), nullable=True),
        sa.Column("correlation_id", sa.String(200), nullable=False),
        sa.Column("causation_id", sa.String(200), nullable=True),
        sa.Column("duration_ms", sa.Numeric(18, 3), nullable=True),
        sa.Column("safe_error_type", sa.String(200), nullable=True),
        sa.Column("result_hash", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', "
            "'skipped_locked', 'skipped_completed')",
            name="paper_validation_runs_valid_status",
        ),
        sa.CheckConstraint(
            "prediction_count >= 0 AND decision_count >= 0 "
            "AND trade_count >= 0 AND settlement_count >= 0",
            name="paper_validation_runs_counts_non_negative",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="paper_validation_runs_duration_non_negative",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL AND duration_ms IS NULL "
            "AND result_hash IS NULL AND safe_error_type IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL)",
            name="paper_validation_runs_terminal_state",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["paper_portfolios.portfolio_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_paper_validation_runs_cycle_started",
        "paper_validation_runs",
        ["cycle_key", "started_at"],
    )
    op.create_index(
        "ix_paper_validation_runs_status_started",
        "paper_validation_runs",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_validation_runs_status_started",
        table_name="paper_validation_runs",
    )
    op.drop_index(
        "ix_paper_validation_runs_cycle_started",
        table_name="paper_validation_runs",
    )
    op.drop_table("paper_validation_runs")
