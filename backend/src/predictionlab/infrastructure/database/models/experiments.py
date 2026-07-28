"""Durable experiment audit models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base


class ExperimentRunModel(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="experiment_runs_valid_status",
        ),
        CheckConstraint(
            "random_seed >= 0",
            name="experiment_runs_non_negative_seed",
        ),
        CheckConstraint(
            "replay_end >= replay_start",
            name="experiment_runs_valid_replay_range",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL "
            "AND result_hash IS NULL AND safe_error_type IS NULL) OR "
            "(status = 'completed' AND finished_at IS NOT NULL "
            "AND result_hash IS NOT NULL AND safe_error_type IS NULL) OR "
            "(status = 'failed' AND finished_at IS NOT NULL "
            "AND safe_error_type IS NOT NULL)",
            name="experiment_runs_valid_terminal_state",
        ),
    )

    experiment_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    replay_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    code_version: Mapped[str | None] = mapped_column(String(200))
    result_hash: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    safe_error_type: Mapped[str | None] = mapped_column(String(200))
