from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from predictionlab.collectors.models import CollectorRunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCollectorRuns:
    page: int = 1
    page_size: int = 20
    provider_code: str | None = None
    status: CollectorRunStatus | None = None
    started_from: datetime | None = None
    started_to: datetime | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be positive")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if self.provider_code is not None and not self.provider_code.strip():
            raise ValueError("provider_code cannot be blank")
        if (
            self.started_from is not None
            and self.started_to is not None
            and self.started_from > self.started_to
        ):
            raise ValueError("started_from cannot be after started_to")


@dataclass(frozen=True, slots=True)
class CollectorRunDetail:
    run_id: UUID
    provider_code: str
    started_at: datetime
    finished_at: datetime | None
    status: CollectorRunStatus
    markets_fetched: int
    markets_created: int
    markets_updated: int
    markets_unchanged: int
    observations_fetched: int
    observations_created: int
    observations_duplicated: int
    observations_skipped: int
    retry_count: int
    duration_ms: float | None
    safe_error_type: str | None
    correlation_id: str


@dataclass(frozen=True, slots=True)
class CollectorRunPage:
    items: tuple[CollectorRunDetail, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
