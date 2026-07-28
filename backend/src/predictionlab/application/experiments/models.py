from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from predictionlab.domain.experiments import ExperimentRunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ListExperimentRuns:
    page: int = 1
    page_size: int = 20
    dataset_id: str | None = None
    status: ExperimentRunStatus | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be positive")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if self.dataset_id is not None and not self.dataset_id.strip():
            raise ValueError("dataset_id cannot be blank")


@dataclass(frozen=True, slots=True)
class ExperimentRunDetail:
    experiment_run_id: UUID
    dataset_id: str
    dataset_version: str
    started_at: datetime
    finished_at: datetime | None
    status: ExperimentRunStatus
    replay_start: datetime
    replay_end: datetime
    random_seed: int
    configuration_hash: str
    code_version: str | None
    result_hash: str | None
    correlation_id: str
    safe_error_type: str | None
    reproducible: bool


@dataclass(frozen=True, slots=True)
class ExperimentRunPage:
    items: tuple[ExperimentRunDetail, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return 0 if self.total == 0 else (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True)
class ReplayDatasetSummary:
    dataset_id: str
    version: str
    schema_version: str
    created_at: datetime
    description: str
    content_sha256: str
    replay_start: datetime
    replay_end: datetime
    market_count: int
    observation_count: int
