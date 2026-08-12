from datetime import UTC, datetime

import pytest

from predictionlab.application.automation import AutomationControlService, AutomationState

NOW = datetime(2026, 8, 12, 12, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Repository:
    def __init__(self) -> None:
        self.state = AutomationState(paused=False, updated_at=None, reason=None)

    async def get(self) -> AutomationState:
        return self.state

    async def set(self, state: AutomationState) -> None:
        self.state = state


@pytest.mark.asyncio
async def test_operator_can_pause_and_resume_automatic_paper_operation() -> None:
    repository = Repository()
    service = AutomationControlService(repository, clock=Clock())

    paused = await service.pause(reason="operator stop")
    resumed = await service.resume()

    assert paused == AutomationState(paused=True, updated_at=NOW, reason="operator stop")
    assert resumed == AutomationState(paused=False, updated_at=NOW, reason=None)
    assert await service.status() == resumed
