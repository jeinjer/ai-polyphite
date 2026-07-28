"""Domain values for reproducible historical experiment runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ExperimentInvariantError(ValueError):
    pass


class ExperimentRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentRun:
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

    def __post_init__(self) -> None:
        if self.experiment_run_id.int == 0:
            raise ExperimentInvariantError("experiment_run_id must be non-zero")
        for field_name in ("dataset_id", "dataset_version", "correlation_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ExperimentInvariantError(f"{field_name} cannot be blank")
        if self.random_seed < 0:
            raise ExperimentInvariantError("random_seed cannot be negative")
        if not _SHA256_PATTERN.fullmatch(self.configuration_hash):
            raise ExperimentInvariantError("configuration_hash must be SHA-256")
        if self.result_hash is not None and not _SHA256_PATTERN.fullmatch(self.result_hash):
            raise ExperimentInvariantError("result_hash must be SHA-256")
        for field_name in ("started_at", "replay_start", "replay_end"):
            object.__setattr__(
                self,
                field_name,
                _utc(getattr(self, field_name), field_name),
            )
        if self.finished_at is not None:
            object.__setattr__(
                self,
                "finished_at",
                _utc(self.finished_at, "finished_at"),
            )
        if self.replay_end < self.replay_start:
            raise ExperimentInvariantError("replay_end cannot precede replay_start")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ExperimentInvariantError("finished_at cannot precede started_at")
        if self.status is ExperimentRunStatus.RUNNING:
            if self.finished_at is not None or self.result_hash is not None:
                raise ExperimentInvariantError("running experiments cannot be finalized")
            if self.safe_error_type is not None:
                raise ExperimentInvariantError("running experiments cannot have an error")
        elif self.finished_at is None:
            raise ExperimentInvariantError("finished experiments require finished_at")
        if (
            self.status is ExperimentRunStatus.COMPLETED
            and (self.result_hash is None or self.safe_error_type is not None)
        ):
            raise ExperimentInvariantError("completed experiments require only a result hash")
        if self.status is ExperimentRunStatus.FAILED and self.safe_error_type is None:
            raise ExperimentInvariantError("failed experiments require a safe error type")

    @property
    def reproducible(self) -> bool:
        return self.status is ExperimentRunStatus.COMPLETED and self.result_hash is not None

    def complete(
        self,
        *,
        finished_at: datetime,
        replay_end: datetime,
        result_hash: str,
    ) -> ExperimentRun:
        if self.status is not ExperimentRunStatus.RUNNING:
            raise ExperimentInvariantError("only running experiments can complete")
        return replace(
            self,
            finished_at=finished_at,
            status=ExperimentRunStatus.COMPLETED,
            replay_end=replay_end,
            result_hash=result_hash,
        )

    def fail(
        self,
        *,
        finished_at: datetime,
        replay_end: datetime,
        safe_error_type: str,
    ) -> ExperimentRun:
        if self.status is not ExperimentRunStatus.RUNNING:
            raise ExperimentInvariantError("only running experiments can fail")
        if not safe_error_type.strip():
            raise ExperimentInvariantError("safe_error_type cannot be blank")
        return replace(
            self,
            finished_at=finished_at,
            status=ExperimentRunStatus.FAILED,
            replay_end=replay_end,
            safe_error_type=safe_error_type.strip(),
        )


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExperimentInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)
