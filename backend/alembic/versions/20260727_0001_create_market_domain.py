"""Create market domain tables.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create providers, markets and immutable market snapshots."""

    op.create_table(
        "providers",
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("char_length(code) > 0", name="ck_providers_code_not_blank"),
        sa.CheckConstraint("char_length(name) > 0", name="ck_providers_name_not_blank"),
        sa.PrimaryKeyConstraint("provider_id", name="pk_providers"),
        sa.UniqueConstraint("code", name="uq_providers_code"),
    )
    op.create_table(
        "markets",
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("provider_market_id", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=1_000), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=200), nullable=True),
        sa.Column("resolution_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(provider_market_id) > 0",
            name="ck_markets_provider_market_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(title) > 0",
            name="ck_markets_title_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'resolved', 'cancelled')",
            name="ck_markets_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            name="fk_markets_provider_id_providers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("market_id", name="pk_markets"),
        sa.UniqueConstraint(
            "provider_id",
            "provider_market_id",
            name="uq_markets_provider_reference",
        ),
    )
    op.create_index("ix_markets_category", "markets", ["category"])
    op.create_index("ix_markets_resolution_at", "markets", ["resolution_at"])
    op.create_index("ix_markets_status", "markets", ["status"])

    op.create_table(
        "market_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("market_id", sa.Uuid(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("yes_price", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("no_price", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("probability", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("spread", sa.Numeric(precision=12, scale=10), nullable=False),
        sa.Column("volume", sa.Numeric(precision=28, scale=8), nullable=False),
        sa.Column("liquidity", sa.Numeric(precision=28, scale=8), nullable=False),
        sa.CheckConstraint(
            "liquidity >= 0",
            name="ck_market_snapshots_liquidity_non_negative",
        ),
        sa.CheckConstraint(
            "no_price >= 0 AND no_price <= 1",
            name="ck_market_snapshots_no_price_range",
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_market_snapshots_probability_range",
        ),
        sa.CheckConstraint(
            "spread >= 0 AND spread <= 1",
            name="ck_market_snapshots_spread_range",
        ),
        sa.CheckConstraint(
            "volume >= 0",
            name="ck_market_snapshots_volume_non_negative",
        ),
        sa.CheckConstraint(
            "yes_price >= 0 AND yes_price <= 1",
            name="ck_market_snapshots_yes_price_range",
        ),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.market_id"],
            name="fk_market_snapshots_market_id_markets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_market_snapshots"),
        sa.UniqueConstraint(
            "market_id",
            "observed_at",
            name="uq_market_snapshots_market_observed_at",
        ),
    )
    op.create_index(
        "ix_market_snapshots_market_observed_at",
        "market_snapshots",
        ["market_id", "observed_at"],
    )


def downgrade() -> None:
    """Remove market domain tables in reverse dependency order."""

    op.drop_index(
        "ix_market_snapshots_market_observed_at",
        table_name="market_snapshots",
    )
    op.drop_table("market_snapshots")
    op.drop_index("ix_markets_status", table_name="markets")
    op.drop_index("ix_markets_resolution_at", table_name="markets")
    op.drop_index("ix_markets_category", table_name="markets")
    op.drop_table("markets")
    op.drop_table("providers")
