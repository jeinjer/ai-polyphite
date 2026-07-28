"""Collector configuration, checkpoints and observable run results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectorCheckpoint:
    provider_code: str
    cursor: str | None
    watermark: datetime | None
    pending_watermark: datetime | None
    updated_at: datetime

    def __post_init__(self) -> None:
        if not _PROVIDER_CODE_PATTERN.fullmatch(self.provider_code):
            raise ValueError("Invalid checkpoint provider code.")
        if self.cursor is not None and not 1 <= len(self.cursor) <= 2048:
            raise ValueError("Checkpoint cursor must contain 1 to 2048 characters.")
        normalized_watermark = (
            _utc(self.watermark, "watermark") if self.watermark is not None else None
        )
        normalized_pending = (
            _utc(self.pending_watermark, "pending_watermark")
            if self.pending_watermark is not None
            else None
        )
        if (
            normalized_watermark is not None
            and normalized_pending is not None
            and normalized_pending < normalized_watermark
        ):
            raise ValueError("pending_watermark cannot precede watermark.")
        object.__setattr__(self, "watermark", normalized_watermark)
        object.__setattr__(self, "pending_watermark", normalized_pending)
        object.__setattr__(self, "updated_at", _utc(self.updated_at, "updated_at"))


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectorConfig:
    page_size: int = 100
    max_pages_per_run: int = 10_000
    watermark_overlap_seconds: float = 1.0
    collect_latest_snapshots: bool = True
    collect_latest_observations: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= 500:
            raise ValueError("page_size must be between 1 and 500.")
        if self.max_pages_per_run < 1:
            raise ValueError("max_pages_per_run must be positive.")
        if not isfinite(self.watermark_overlap_seconds) or self.watermark_overlap_seconds < 0:
            raise ValueError("watermark_overlap_seconds must be finite and non-negative.")


class CollectorRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCEEDED = "completed"
    SKIPPED_LOCKED = "skipped_locked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectorRunStarted:
    run_id: UUID
    provider_code: str
    started_at: datetime
    correlation_id: str

    def __post_init__(self) -> None:
        if self.run_id.int == 0:
            raise ValueError("run_id must be a non-zero UUID.")
        if not _PROVIDER_CODE_PATTERN.fullmatch(self.provider_code):
            raise ValueError("Invalid collector run provider code.")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id cannot be blank.")
        object.__setattr__(
            self,
            "started_at",
            _utc(self.started_at, "started_at"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectorRunResult:
    run_id: UUID
    provider_code: str
    correlation_id: str
    causation_id: str | None
    status: CollectorRunStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    cursor_before: str | None
    cursor_after: str | None
    watermark_before: datetime | None
    watermark_after: datetime | None
    pages: int = 0
    markets_fetched: int = 0
    markets_created: int = 0
    markets_updated: int = 0
    markets_unchanged: int = 0
    snapshots_fetched: int = 0
    snapshots_created: int = 0
    snapshots_duplicate: int = 0
    snapshots_skipped: int = 0
    observations_fetched: int = 0
    observations_created: int = 0
    observations_duplicate: int = 0
    observations_skipped: int = 0
    retries: int = 0
    error_type: str | None = None
