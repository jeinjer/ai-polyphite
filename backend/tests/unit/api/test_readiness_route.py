from __future__ import annotations

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.health import (
    ComponentHealth,
    ComponentStatus,
    ReadinessReport,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings


class StubReadinessChecker:
    def __init__(self, report: ReadinessReport) -> None:
        self._report = report

    async def check(self) -> ReadinessReport:
        return self._report


def create_test_app(report: ReadinessReport):
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
        )
    )
    application.state.readiness_checker = StubReadinessChecker(report)
    return application


@pytest.mark.asyncio
async def test_readiness_returns_ok_when_all_dependencies_are_up() -> None:
    application = create_test_app(
        ReadinessReport(
            checks=(
                ComponentHealth("postgres", ComponentStatus.UP, 1.25),
                ComponentHealth("redis", ComponentStatus.UP, 0.5),
            )
        )
    )
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": [
            {"name": "postgres", "status": "up", "latency_ms": 1.25},
            {"name": "redis", "status": "up", "latency_ms": 0.5},
        ],
    }


@pytest.mark.asyncio
async def test_readiness_returns_503_when_a_dependency_is_down() -> None:
    application = create_test_app(
        ReadinessReport(
            checks=(
                ComponentHealth("postgres", ComponentStatus.DOWN, 2.0),
                ComponentHealth("redis", ComponentStatus.UP, 0.5),
            )
        )
    )
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
