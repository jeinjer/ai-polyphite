from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from predictionlab.application.paper_validation import (
    PaperValidationRunResult,
    PaperValidationRunStatus,
)
from predictionlab.runtime.paper_validation_worker import (
    PaperValidationWorker,
    _scheduled_slot,
)

NOW = datetime(2026, 7, 28, 12, 34, 56, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW

    def __call__(self) -> datetime:
        return self.now()


class RecordingRunner:
    def __init__(self) -> None:
        self.calls = []
        self.called = asyncio.Event()

    async def run_cycle(
        self,
        *,
        scheduled_for,
        correlation_id=None,
        causation_id=None,
    ):
        self.calls.append((scheduled_for, correlation_id, causation_id))
        self.called.set()
        return PaperValidationRunResult(
            run_id=__import__("uuid").uuid4(),
            cycle_key="a" * 64,
            scheduled_for=scheduled_for,
            started_at=NOW,
            finished_at=NOW,
            duration_ms=0,
            status=PaperValidationRunStatus.COMPLETED,
            correlation_id=correlation_id or "test",
            causation_id=causation_id,
        )


def test_scheduled_slot_is_utc_and_stable() -> None:
    assert _scheduled_slot(NOW, 3600) == datetime(
        2026,
        7,
        28,
        12,
        tzinfo=UTC,
    )


@pytest.mark.asyncio
async def test_run_once_uses_current_logical_slot() -> None:
    runner = RecordingRunner()
    worker = PaperValidationWorker(
        runner=runner,
        interval_seconds=3600,
        run_immediately=True,
        clock=FixedClock(),
    )

    result = await worker.run_once()

    assert result.status is PaperValidationRunStatus.COMPLETED
    assert runner.calls[0][0] == datetime(2026, 7, 28, 12, tzinfo=UTC)
    assert runner.calls[0][2] == "paper-validation-once"


@pytest.mark.asyncio
async def test_periodic_worker_stops_cooperatively() -> None:
    runner = RecordingRunner()
    worker = PaperValidationWorker(
        runner=runner,
        interval_seconds=3600,
        run_immediately=True,
        clock=FixedClock(),
    )

    task = asyncio.create_task(worker.run())
    await asyncio.wait_for(runner.called.wait(), timeout=1)
    worker.stop()
    await asyncio.wait_for(task, timeout=1)

    assert len(runner.calls) == 1
    assert runner.calls[0][2] == "paper-validation-interval"
