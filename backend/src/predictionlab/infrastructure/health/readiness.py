from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from time import perf_counter

from predictionlab.application.health import (
    ComponentHealth,
    ComponentStatus,
    ReadinessReport,
)

logger = logging.getLogger(__name__)

type CheckCallable = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    name: str
    run: CheckCallable


class ReadinessService:
    def __init__(
        self,
        *,
        checks: Sequence[DependencyCheck],
        timeout_seconds: float,
    ) -> None:
        self._checks = tuple(checks)
        self._timeout_seconds = timeout_seconds

    async def check(self) -> ReadinessReport:
        results = await asyncio.gather(*(self._execute(check) for check in self._checks))
        return ReadinessReport(checks=tuple(results))

    async def _execute(self, check: DependencyCheck) -> ComponentHealth:
        started_at = perf_counter()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                await check.run()
        except Exception as exc:
            latency_ms = _duration_ms(started_at)
            logger.warning(
                "readiness_dependency_unavailable",
                extra={
                    "component": check.name,
                    "duration_ms": latency_ms,
                    "error_type": type(exc).__name__,
                },
            )
            return ComponentHealth(
                name=check.name,
                status=ComponentStatus.DOWN,
                latency_ms=latency_ms,
            )

        return ComponentHealth(
            name=check.name,
            status=ComponentStatus.UP,
            latency_ms=_duration_ms(started_at),
        )


def _duration_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
