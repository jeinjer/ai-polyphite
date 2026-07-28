"""Periodic collector worker with cooperative shutdown."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Protocol
from uuid import uuid4

from predictionlab.collectors import CollectorRunFailedError, CollectorRunResult

logger = logging.getLogger(__name__)


class CollectorRunner(Protocol):
    async def collect(
        self,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CollectorRunResult: ...


class CollectorWorker:
    def __init__(
        self,
        *,
        collectors: Mapping[str, CollectorRunner],
        intervals_seconds: Mapping[str, float],
        run_immediately: bool,
    ) -> None:
        if not collectors:
            raise ValueError("CollectorWorker requires at least one collector.")
        if set(collectors) != set(intervals_seconds):
            raise ValueError("Every collector requires one interval.")
        if any(interval <= 0 for interval in intervals_seconds.values()):
            raise ValueError("Collector intervals must be positive.")
        self._collectors = dict(collectors)
        self._intervals = dict(intervals_seconds)
        self._run_immediately = run_immediately
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        logger.info(
            "collector_worker_started",
            extra={"provider_codes": sorted(self._collectors)},
        )
        try:
            async with asyncio.TaskGroup() as tasks:
                for provider_code, collector in self._collectors.items():
                    tasks.create_task(
                        self._run_provider_loop(
                            provider_code,
                            collector,
                        ),
                        name=f"collector-{provider_code}",
                    )
        finally:
            logger.info("collector_worker_stopped")

    async def run_once(self, provider_code: str) -> CollectorRunResult:
        collector = self._collectors.get(provider_code)
        if collector is None:
            known = ", ".join(sorted(self._collectors))
            raise ValueError(f"Provider '{provider_code}' is not enabled. Enabled: {known}.")
        return await collector.collect(
            correlation_id=f"manual-{uuid4()}",
            causation_id="collector-once",
        )

    def stop(self) -> None:
        self._stop_event.set()

    async def _run_provider_loop(
        self,
        provider_code: str,
        collector: CollectorRunner,
    ) -> None:
        if not self._run_immediately and await self._wait(self._intervals[provider_code]):
            return
        while not self._stop_event.is_set():
            try:
                await collector.collect(
                    correlation_id=f"worker-{uuid4()}",
                    causation_id="collector-interval",
                )
            except CollectorRunFailedError as exc:
                logger.error(
                    "collector_worker_cycle_failed",
                    extra={
                        "provider_code": provider_code,
                        "collector_run_id": str(exc.result.run_id),
                        "error_type": exc.result.error_type,
                        "retryable": exc.retryable,
                    },
                )
            if await self._wait(self._intervals[provider_code]):
                return

    async def _wait(self, delay: float) -> bool:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
        except TimeoutError:
            return False
        return True
