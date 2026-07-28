from __future__ import annotations

import pytest

from predictionlab.application.health import ComponentStatus
from predictionlab.core.settings import AppEnvironment, Settings
from predictionlab.infrastructure.resources import create_resources


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_and_redis_are_ready() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
    )
    resources = create_resources(settings)

    try:
        report = await resources.readiness.check()
    finally:
        await resources.close()

    assert report.ready is True
    assert {check.name for check in report.checks} == {"postgres", "redis"}
    assert all(check.status is ComponentStatus.UP for check in report.checks)
