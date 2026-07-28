from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from predictionlab.collectors import CollectorRunResult, CollectorRunStatus
from predictionlab.runtime.collector_worker import CollectorWorker

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


class RecordingCollector:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str | None]] = []
        self.called = asyncio.Event()

    async def collect(
        self,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CollectorRunResult:
        self.calls.append((correlation_id, causation_id))
        self.called.set()
        return CollectorRunResult(
            run_id=uuid4(),
            provider_code="mock",
            correlation_id=correlation_id or "test",
            causation_id=causation_id,
            status=CollectorRunStatus.COMPLETED,
            started_at=NOW,
            finished_at=NOW,
            duration_ms=0,
            cursor_before=None,
            cursor_after=None,
            watermark_before=None,
            watermark_after=None,
        )


@pytest.mark.asyncio
async def test_worker_run_once_targets_only_requested_provider() -> None:
    mock = RecordingCollector()
    manifold = RecordingCollector()
    worker = CollectorWorker(
        collectors={"mock": mock, "manifold": manifold},
        intervals_seconds={"mock": 10, "manifold": 20},
        run_immediately=False,
    )

    result = await worker.run_once("mock")

    assert result.status is CollectorRunStatus.COMPLETED
    assert len(mock.calls) == 1
    assert manifold.calls == []
    assert mock.calls[0][1] == "collector-once"


@pytest.mark.asyncio
async def test_periodic_worker_runs_immediately_and_stops_cooperatively() -> None:
    collector = RecordingCollector()
    worker = CollectorWorker(
        collectors={"mock": collector},
        intervals_seconds={"mock": 60},
        run_immediately=True,
    )

    task = asyncio.create_task(worker.run())
    await asyncio.wait_for(collector.called.wait(), timeout=1)
    worker.stop()
    await asyncio.wait_for(task, timeout=1)

    assert len(collector.calls) == 1
    assert collector.calls[0][1] == "collector-interval"


@pytest.mark.asyncio
async def test_worker_rejects_run_once_for_disabled_provider() -> None:
    worker = CollectorWorker(
        collectors={"mock": RecordingCollector()},
        intervals_seconds={"mock": 60},
        run_immediately=False,
    )

    with pytest.raises(ValueError, match="not enabled"):
        await worker.run_once("manifold")
