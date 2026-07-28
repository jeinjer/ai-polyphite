"""Add historical observations and explicit market resolution.

Revision ID: 20260728_0004
Revises: 20260728_0003
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0004"
down_revision: str | Sequence[str] | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable-safe history while preserving every existing market."""

    op.add_column(
        "markets",
        sa.Column(
            "resolution_outcome",
            sa.String(length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "markets",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "markets",
        sa.Column("resolution_source", sa.String(length=200), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE markets SET resolution_outcome = CASE "
            "WHEN status = 'cancelled' THEN 'cancelled' "
            "WHEN status = 'resolved' THEN 'other' "
            "ELSE 'unresolved' END"
        )
    )
    op.alter_column(
        "markets",
        "resolution_outcome",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.create_check_constraint(
        "market_resolution_coherent",
        "markets",
        "("
        "(status IN ('open', 'closed') AND resolution_outcome = 'unresolved') "
        "OR (status = 'resolved' AND resolution_outcome IN ('yes', 'no', 'other')) "
        "OR (status = 'cancelled' AND resolution_outcome = 'cancelled')"
        ")",
    )
    op.create_check_constraint(
        "market_resolution_source_not_blank",
        "markets",
        "resolution_source IS NULL OR char_length(resolution_source) > 0",
    )

    op.create_table(
        "market_observations",
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("probability", sa.Numeric(12, 10), nullable=True),
        sa.Column("volume", sa.Numeric(28, 8), nullable=True),
        sa.Column("liquidity", sa.Numeric(28, 8), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("raw_payload_hash", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "probability IS NULL OR (probability >= 0 AND probability <= 1)",
            name="market_observations_probability_range",
        ),
        sa.CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="market_observations_volume_non_negative",
        ),
        sa.CheckConstraint(
            "liquidity IS NULL OR liquidity >= 0",
            name="market_observations_liquidity_non_negative",
        ),
        sa.CheckConstraint(
            "probability IS NOT NULL OR volume IS NOT NULL OR liquidity IS NOT NULL",
            name="market_observations_has_value",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provider_code"],
            ["providers.code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint(
            "market_id",
            "observed_at",
            name="uq_market_observations_market_observed_at",
        ),
    )
    op.create_index(
        "ix_market_observations_market_observed_at",
        "market_observations",
        ["market_id", "observed_at"],
    )
    op.create_index(
        "ix_market_observations_provider_observed_at",
        "market_observations",
        ["provider_code", "observed_at"],
    )

    op.create_table(
        "market_state_history",
        sa.Column("change_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "previous_resolution_outcome",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column("resolution_outcome", sa.String(length=32), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_source", sa.String(length=200), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'resolved', 'cancelled')",
            name="market_state_history_valid_status",
        ),
        sa.CheckConstraint(
            "resolution_outcome IN "
            "('unresolved', 'yes', 'no', 'cancelled', 'other')",
            name="market_state_history_valid_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("change_id"),
    )
    op.create_index(
        "ix_market_state_history_market_occurred_at",
        "market_state_history",
        ["market_id", "occurred_at"],
    )


def downgrade() -> None:
    """Remove the additive history slice and restore the previous schema."""

    op.drop_index(
        "ix_market_state_history_market_occurred_at",
        table_name="market_state_history",
    )
    op.drop_table("market_state_history")
    op.drop_index(
        "ix_market_observations_provider_observed_at",
        table_name="market_observations",
    )
    op.drop_index(
        "ix_market_observations_market_observed_at",
        table_name="market_observations",
    )
    op.drop_table("market_observations")
    op.drop_constraint(
        "market_resolution_source_not_blank",
        "markets",
        type_="check",
    )
    op.drop_constraint(
        "market_resolution_coherent",
        "markets",
        type_="check",
    )
    op.drop_column("markets", "resolution_source")
    op.drop_column("markets", "resolved_at")
    op.drop_column("markets", "resolution_outcome")
