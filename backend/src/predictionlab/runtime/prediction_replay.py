"""Prediction scheduling over replay events without exposing future data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from predictionlab.application.predictions import PredictionOrchestrator
from predictionlab.domain.predictions import PredictionRun


class ReplayPredictionSchedule:
    def __init__(
        self,
        *,
        replay_start: datetime,
        replay_end: datetime,
        interval: timedelta | None = None,
        timestamps: tuple[datetime, ...] = (),
    ) -> None:
        replay_start = _utc(replay_start, "replay_start")
        replay_end = _utc(replay_end, "replay_end")
        if interval is None and not timestamps:
            raise ValueError("an interval or explicit timestamps are required")
        if interval is not None and interval <= timedelta(0):
            raise ValueError("prediction interval must be positive")
        explicit = tuple(
            sorted({_utc(value, "prediction timestamp") for value in timestamps})
        )
        if any(value < replay_start or value > replay_end for value in explicit):
            raise ValueError("prediction timestamps must be inside the replay range")
        generated: list[datetime] = []
        if interval is not None:
            current = replay_start
            while current <= replay_end:
                generated.append(current)
                current += interval
        self._timestamps = tuple(sorted(set([*explicit, *generated])))
        self._index = 0

    @property
    def timestamps(self) -> tuple[datetime, ...]:
        return self._timestamps

    def due(self, visible_at: datetime) -> tuple[datetime, ...]:
        start = self._index
        while (
            self._index < len(self._timestamps)
            and self._timestamps[self._index] <= visible_at
        ):
            self._index += 1
        return self._timestamps[start : self._index]


class PredictionReplayHook:
    def __init__(
        self,
        *,
        orchestrator: PredictionOrchestrator,
        schedule: ReplayPredictionSchedule,
        random_seed: int,
    ) -> None:
        self._orchestrator = orchestrator
        self._schedule = schedule
        self._random_seed = random_seed
        self.prediction_count = 0
        self.last_prediction_runs: tuple[PredictionRun, ...] = ()

    async def __call__(
        self,
        experiment_run_id: UUID,
        visible_at: datetime,
        correlation_id: str,
    ) -> tuple[str, ...]:
        result_hashes: list[str] = []
        current_runs: list[PredictionRun] = []
        for predicted_at in self._schedule.due(visible_at):
            predictions = await self._orchestrator.run_batch(
                predicted_at=predicted_at,
                experiment_run_id=experiment_run_id,
                random_seed=self._random_seed,
                correlation_id=correlation_id,
                causation_id=f"replay-predict:{predicted_at.isoformat()}",
            )
            current_runs.extend(predictions)
            result_hashes.extend(item.result_hash for item in predictions)
            self.prediction_count += len(predictions)
        self.last_prediction_runs = tuple(current_runs)
        return tuple(result_hashes)


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)
