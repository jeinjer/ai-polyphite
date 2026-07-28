"""Add deterministic prediction runs and per-agent outputs.

Revision ID: 20260728_0007
Revises: 20260728_0006
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0007"
down_revision: str | Sequence[str] | None = "20260728_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prediction_runs",
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_run_id", sa.Uuid(), nullable=True),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("consensus_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("consensus_confidence", sa.Numeric(12, 10), nullable=False),
        sa.Column("recommendation", sa.String(32), nullable=False),
        sa.Column("edge", sa.Numeric(12, 10), nullable=True),
        sa.Column("no_edge", sa.Numeric(12, 10), nullable=True),
        sa.Column("opportunity_level", sa.String(32), nullable=False),
        sa.Column("disagreement_score", sa.Numeric(12, 10), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("agent_configuration_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("duration_ms", sa.Numeric(18, 3), nullable=False),
        sa.Column("safe_error_type", sa.String(200), nullable=True),
        sa.Column("abstention_reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(200), nullable=False),
        sa.Column("causation_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_weights", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed', 'abstained', 'failed')",
            name="prediction_runs_valid_status",
        ),
        sa.CheckConstraint(
            "recommendation IN ('yes', 'no', 'abstain')",
            name="prediction_runs_valid_recommendation",
        ),
        sa.CheckConstraint(
            "opportunity_level IN ('none', 'weak', 'moderate', 'strong')",
            name="prediction_runs_valid_opportunity",
        ),
        sa.CheckConstraint(
            "market_probability IS NULL OR "
            "(market_probability >= 0 AND market_probability <= 1)",
            name="prediction_runs_market_probability_range",
        ),
        sa.CheckConstraint(
            "consensus_probability IS NULL OR "
            "(consensus_probability >= 0 AND consensus_probability <= 1)",
            name="prediction_runs_consensus_probability_range",
        ),
        sa.CheckConstraint(
            "consensus_confidence >= 0 AND consensus_confidence <= 1",
            name="prediction_runs_confidence_range",
        ),
        sa.CheckConstraint(
            "disagreement_score >= 0 AND disagreement_score <= 1",
            name="prediction_runs_disagreement_range",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0",
            name="prediction_runs_duration_non_negative",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND recommendation IN ('yes', 'no') "
            "AND consensus_probability IS NOT NULL AND edge IS NOT NULL "
            "AND safe_error_type IS NULL AND abstention_reason IS NULL) OR "
            "(status = 'abstained' AND recommendation = 'abstain' "
            "AND consensus_probability IS NULL AND edge IS NULL "
            "AND safe_error_type IS NULL AND abstention_reason IS NOT NULL) OR "
            "(status = 'failed' AND safe_error_type IS NOT NULL "
            "AND abstention_reason IS NULL)",
            name="prediction_runs_valid_terminal_state",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["experiment_runs.experiment_run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("prediction_run_id"),
        sa.UniqueConstraint(
            "experiment_run_id",
            "market_id",
            "predicted_at",
            "agent_configuration_hash",
            name="uq_prediction_runs_idempotency",
        ),
    )
    for column in ("predicted_at", "recommendation", "opportunity_level", "status"):
        op.create_index(op.f(f"ix_prediction_runs_{column}"), "prediction_runs", [column])
    op.create_index(
        "ix_prediction_runs_market_predicted_at",
        "prediction_runs",
        ["market_id", "predicted_at"],
    )
    op.create_index(
        "ix_prediction_runs_experiment_predicted_at",
        "prediction_runs",
        ["experiment_run_id", "predicted_at"],
    )
    op.create_index(
        "uq_prediction_runs_live_idempotency",
        "prediction_runs",
        ["market_id", "predicted_at", "agent_configuration_hash"],
        unique=True,
        postgresql_where=sa.text("experiment_run_id IS NULL"),
    )
    op.create_table(
        "agent_predictions",
        sa.Column("agent_prediction_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_run_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_version", sa.String(50), nullable=False),
        sa.Column("predicted_probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("confidence", sa.Numeric(12, 10), nullable=False),
        sa.Column("recommendation", sa.String(32), nullable=False),
        sa.Column("rationale_summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("duration_ms", sa.Numeric(18, 3), nullable=False),
        sa.Column("disagreement_score", sa.Numeric(12, 10), nullable=True),
        sa.Column("agent_weights", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "recommendation IN ('yes', 'no', 'abstain')",
            name="agent_predictions_valid_recommendation",
        ),
        sa.CheckConstraint(
            "predicted_probability IS NULL OR "
            "(predicted_probability >= 0 AND predicted_probability <= 1)",
            name="agent_predictions_probability_range",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="agent_predictions_confidence_range",
        ),
        sa.CheckConstraint(
            "disagreement_score IS NULL OR "
            "(disagreement_score >= 0 AND disagreement_score <= 1)",
            name="agent_predictions_disagreement_range",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0",
            name="agent_predictions_duration_non_negative",
        ),
        sa.CheckConstraint(
            "(recommendation = 'abstain' AND predicted_probability IS NULL) OR "
            "(recommendation IN ('yes', 'no') AND predicted_probability IS NOT NULL)",
            name="agent_predictions_recommendation_probability",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_run_id"],
            ["prediction_runs.prediction_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("agent_prediction_id"),
        sa.UniqueConstraint(
            "prediction_run_id",
            "agent_name",
            name="uq_agent_predictions_run_agent",
        ),
    )
    op.create_index(
        "ix_agent_predictions_agent_name_version",
        "agent_predictions",
        ["agent_name", "agent_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_predictions_agent_name_version",
        table_name="agent_predictions",
    )
    op.drop_table("agent_predictions")
    op.drop_index(
        "ix_prediction_runs_experiment_predicted_at",
        table_name="prediction_runs",
    )
    op.drop_index(
        "uq_prediction_runs_live_idempotency",
        table_name="prediction_runs",
    )
    op.drop_index(
        "ix_prediction_runs_market_predicted_at",
        table_name="prediction_runs",
    )
    for column in ("status", "opportunity_level", "recommendation", "predicted_at"):
        op.drop_index(op.f(f"ix_prediction_runs_{column}"), table_name="prediction_runs")
    op.drop_table("prediction_runs")
