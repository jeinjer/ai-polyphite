from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from predictionlab.collectors import (
    CollectorRunResult,
    CollectorRunStatus,
    MarketDataCollector,
)
from predictionlab.core.clock import ReplayClock
from predictionlab.domain.experiments import ExperimentRun
from predictionlab.providers.replay import load_replay_dataset
from predictionlab.runtime.replay_runner import ReplayMode, ReplayRunner

DATASET = Path(__file__).parents[3] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"
WALL_TIME = datetime(2026, 7, 28, tzinfo=UTC)
RUN_ID = UUID("00000000-0000-4000-8000-000000000001")


class MemoryExperimentStore:
    def __init__(self) -> None:
        self.started: list[ExperimentRun] = []
        self.finished: list[ExperimentRun] = []

    async def start(self, run: ExperimentRun) -> None:
        self.started.append(run)

    async def finish(self, run: ExperimentRun) -> None:
        self.finished.append(run)


class DeterministicCollector:
    def __init__(self, clock: ReplayClock) -> None:
        self.clock = clock
        self.calls = 0

    async def collect(
        self,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CollectorRunResult:
        self.calls += 1
        now = self.clock.now()
        return CollectorRunResult(
            run_id=RUN_ID,
            provider_code="replay",
            correlation_id=correlation_id or "test",
            causation_id=causation_id,
            status=CollectorRunStatus.COMPLETED,
            started_at=now,
            finished_at=now,
            duration_ms=0,
            cursor_before=None,
            cursor_after=None,
            watermark_before=None,
            watermark_after=now,
            pages=1,
            markets_fetched=1,
        )


def build_runner() -> tuple[ReplayRunner, ReplayClock, DeterministicCollector]:
    dataset = load_replay_dataset(DATASET)
    clock = ReplayClock(
        start_at=dataset.metadata.replay_start,
        event_times=dataset.event_times,
    )
    collector = DeterministicCollector(clock)
    runner = ReplayRunner(
        metadata=dataset.metadata,
        replay_clock=clock,
        collector=cast(MarketDataCollector, collector),
        experiment_store=MemoryExperimentStore(),
        wall_clock=lambda: WALL_TIME,
        id_factory=lambda: RUN_ID,
        code_version="test",
    )
    return runner, clock, collector


@pytest.mark.asyncio
async def test_step_and_reset_are_explicit() -> None:
    runner, clock, collector = build_runner()

    result = await runner.run(mode=ReplayMode.STEP)
    assert collector.calls == 1
    assert result.experiment.replay_end == clock.start_at

    clock.advance(timedelta(minutes=1))
    assert runner.reset() == clock.start_at
    assert clock.next_event_at == clock.start_at


@pytest.mark.asyncio
async def test_accelerated_runs_are_deterministic() -> None:
    first_runner, _, first_collector = build_runner()
    second_runner, _, second_collector = build_runner()

    first = await first_runner.run(mode=ReplayMode.ACCELERATED, random_seed=42)
    second = await second_runner.run(mode=ReplayMode.ACCELERATED, random_seed=42)

    assert first_collector.calls == second_collector.calls
    assert first.experiment.configuration_hash == second.experiment.configuration_hash
    assert first.experiment.result_hash == second.experiment.result_hash
    assert first.experiment.reproducible is True


@pytest.mark.asyncio
async def test_until_processes_no_future_event() -> None:
    runner, clock, collector = build_runner()
    target = clock.start_at + timedelta(hours=5)
    expected_calls = len([event for event in clock.event_times if event <= target])

    result = await runner.run(mode=ReplayMode.UNTIL, until=target)

    assert collector.calls == expected_calls
    assert clock.now() == target
    assert result.experiment.replay_end == target
    assert clock.next_event_at is None or clock.next_event_at > target
