"""Add durable collector run audit.

Revision ID: 20260728_0005
Revises: 20260728_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0005"
down_revision: str | Sequence[str] | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_runs",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("markets_fetched", sa.Integer(), nullable=False),
        sa.Column("markets_created", sa.Integer(), nullable=False),
        sa.Column("markets_updated", sa.Integer(), nullable=False),
        sa.Column("markets_unchanged", sa.Integer(), nullable=False),
        sa.Column("observations_fetched", sa.Integer(), nullable=False),
        sa.Column("observations_created", sa.Integer(), nullable=False),
        sa.Column("observations_duplicated", sa.Integer(), nullable=False),
        sa.Column("observations_skipped", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("safe_error_type", sa.String(length=200), nullable=True),
        sa.Column("correlation_id", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'skipped_locked')",
            name="collector_runs_valid_status",
        ),
        sa.CheckConstraint(
            "markets_fetched >= 0 AND markets_created >= 0 "
            "AND markets_updated >= 0 AND markets_unchanged >= 0 "
            "AND observations_fetched >= 0 AND observations_created >= 0 "
            "AND observations_duplicated >= 0 AND observations_skipped >= 0 "
            "AND retry_count >= 0",
            name="collector_runs_non_negative_counters",
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        op.f("ix_collector_runs_provider_code"),
        "collector_runs",
        ["provider_code"],
    )
    op.create_index(
        op.f("ix_collector_runs_started_at"),
        "collector_runs",
        ["started_at"],
    )
    op.create_index(
        op.f("ix_collector_runs_status"),
        "collector_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_collector_runs_status"), table_name="collector_runs")
    op.drop_index(
        op.f("ix_collector_runs_started_at"),
        table_name="collector_runs",
    )
    op.drop_index(
        op.f("ix_collector_runs_provider_code"),
        table_name="collector_runs",
    )
    op.drop_table("collector_runs")
