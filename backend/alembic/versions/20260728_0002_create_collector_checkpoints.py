"""Create durable collector checkpoints.

Revision ID: 20260728_0002
Revises: 20260727_0001
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0002"
down_revision: str | Sequence[str] | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create resumable state for one catalog stream per provider."""

    op.create_table(
        "collector_checkpoints",
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("cursor", sa.String(length=2_048), nullable=True),
        sa.Column("watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pending_watermark", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "cursor IS NULL OR char_length(cursor) > 0",
            name="ck_collector_checkpoints_cursor_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(provider_code) > 0",
            name="ck_collector_checkpoints_provider_code_not_blank",
        ),
        sa.PrimaryKeyConstraint(
            "provider_code",
            name="pk_collector_checkpoints",
        ),
    )


def downgrade() -> None:
    """Remove collector checkpoints."""

    op.drop_table("collector_checkpoints")
