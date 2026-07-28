"""Split external market creation from local ingestion.

Revision ID: 20260728_0003
Revises: 20260728_0002
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0003"
down_revision: str | Sequence[str] | None = "20260728_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Preserve local creation values and add nullable source provenance."""

    op.alter_column(
        "markets",
        "created_at",
        new_column_name="ingested_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.add_column(
        "markets",
        sa.Column(
            "source_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Restore the previous single local timestamp."""

    op.drop_column("markets", "source_created_at")
    op.alter_column(
        "markets",
        "ingested_at",
        new_column_name="created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
