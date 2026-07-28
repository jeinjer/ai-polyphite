"""Durable collector state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base


class CollectorCheckpointModel(Base):
    __tablename__ = "collector_checkpoints"
    __table_args__ = (
        CheckConstraint(
            "char_length(provider_code) > 0",
            name="provider_code_not_blank",
        ),
        CheckConstraint(
            "cursor IS NULL OR char_length(cursor) > 0",
            name="cursor_not_blank",
        ),
    )

    provider_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(String(2_048))
    watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CollectorRunModel(Base):
    __tablename__ = "collector_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'skipped_locked')",
            name="collector_runs_valid_status",
        ),
        CheckConstraint(
            "markets_fetched >= 0 AND markets_created >= 0 "
            "AND markets_updated >= 0 AND markets_unchanged >= 0 "
            "AND observations_fetched >= 0 AND observations_created >= 0 "
            "AND observations_duplicated >= 0 AND observations_skipped >= 0 "
            "AND retry_count >= 0",
            name="collector_runs_non_negative_counters",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    markets_fetched: Mapped[int] = mapped_column(Integer, nullable=False)
    markets_created: Mapped[int] = mapped_column(Integer, nullable=False)
    markets_updated: Mapped[int] = mapped_column(Integer, nullable=False)
    markets_unchanged: Mapped[int] = mapped_column(Integer, nullable=False)
    observations_fetched: Mapped[int] = mapped_column(Integer, nullable=False)
    observations_created: Mapped[int] = mapped_column(Integer, nullable=False)
    observations_duplicated: Mapped[int] = mapped_column(Integer, nullable=False)
    observations_skipped: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    safe_error_type: Mapped[str | None] = mapped_column(String(200))
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
