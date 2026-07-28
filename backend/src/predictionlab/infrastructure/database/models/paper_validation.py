"""Durable audit records for continuous paper validation attempts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base


class PaperValidationRunModel(Base):
    __tablename__ = "paper_validation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', "
            "'skipped_locked', 'skipped_completed')",
            name="paper_validation_runs_valid_status",
        ),
        CheckConstraint(
            "prediction_count >= 0 AND decision_count >= 0 "
            "AND trade_count >= 0 AND settlement_count >= 0",
            name="paper_validation_runs_counts_non_negative",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="paper_validation_runs_duration_non_negative",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL AND duration_ms IS NULL "
            "AND result_hash IS NULL AND safe_error_type IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL)",
            name="paper_validation_runs_terminal_state",
        ),
        Index(
            "ix_paper_validation_runs_cycle_started",
            "cycle_key",
            "started_at",
        ),
        Index(
            "ix_paper_validation_runs_status_started",
            "status",
            "started_at",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    cycle_key: Mapped[str] = mapped_column(String(64), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    portfolio_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
    )
    prediction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    settlement_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconciliation_ok: Mapped[bool | None] = mapped_column(Boolean)
    reconciliation_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reconciliation_result_hash: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(200))
    duration_ms: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    safe_error_type: Mapped[str | None] = mapped_column(String(200))
    result_hash: Mapped[str | None] = mapped_column(String(64))
