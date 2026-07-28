"""Add reproducible experiment run audit.

Revision ID: 20260728_0006
Revises: 20260728_0005
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0006"
down_revision: str | Sequence[str] | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_runs",
        sa.Column("experiment_run_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("replay_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replay_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("configuration_hash", sa.String(length=64), nullable=False),
        sa.Column("code_version", sa.String(length=200), nullable=True),
        sa.Column("result_hash", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=200), nullable=False),
        sa.Column("safe_error_type", sa.String(length=200), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="experiment_runs_valid_status",
        ),
        sa.CheckConstraint(
            "random_seed >= 0",
            name="experiment_runs_non_negative_seed",
        ),
        sa.CheckConstraint(
            "replay_end >= replay_start",
            name="experiment_runs_valid_replay_range",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL "
            "AND result_hash IS NULL AND safe_error_type IS NULL) OR "
            "(status = 'completed' AND finished_at IS NOT NULL "
            "AND result_hash IS NOT NULL AND safe_error_type IS NULL) OR "
            "(status = 'failed' AND finished_at IS NOT NULL "
            "AND safe_error_type IS NOT NULL)",
            name="experiment_runs_valid_terminal_state",
        ),
        sa.PrimaryKeyConstraint("experiment_run_id"),
    )
    op.create_index(
        op.f("ix_experiment_runs_dataset_id"),
        "experiment_runs",
        ["dataset_id"],
    )
    op.create_index(
        op.f("ix_experiment_runs_started_at"),
        "experiment_runs",
        ["started_at"],
    )
    op.create_index(
        op.f("ix_experiment_runs_status"),
        "experiment_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_experiment_runs_status"), table_name="experiment_runs")
    op.drop_index(op.f("ix_experiment_runs_started_at"), table_name="experiment_runs")
    op.drop_index(op.f("ix_experiment_runs_dataset_id"), table_name="experiment_runs")
    op.drop_table("experiment_runs")
