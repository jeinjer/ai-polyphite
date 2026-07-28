from __future__ import annotations

import asyncio

import pytest

from predictionlab.application.health import ComponentStatus
from predictionlab.infrastructure.health.readiness import (
    DependencyCheck,
    ReadinessService,
)


async def successful_check() -> None:
    return None


async def failing_check() -> None:
    raise ConnectionError


async def slow_check() -> None:
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_readiness_service_reports_each_dependency() -> None:
    service = ReadinessService(
        checks=(
            DependencyCheck("postgres", successful_check),
            DependencyCheck("redis", failing_check),
        ),
        timeout_seconds=1.0,
    )

    report = await service.check()

    assert report.ready is False
    assert report.checks[0].status is ComponentStatus.UP
    assert report.checks[1].status is ComponentStatus.DOWN
    assert all(check.latency_ms >= 0 for check in report.checks)


@pytest.mark.asyncio
async def test_readiness_service_enforces_timeout() -> None:
    service = ReadinessService(
        checks=(DependencyCheck("slow", slow_check),),
        timeout_seconds=0.001,
    )

    report = await service.check()

    assert report.ready is False
    assert report.checks[0].status is ComponentStatus.DOWN
