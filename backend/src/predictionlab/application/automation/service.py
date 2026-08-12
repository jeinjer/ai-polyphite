"""Operator control for the autonomous paper-validation loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from predictionlab.core.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class AutomationState:
    paused: bool
    updated_at: datetime | None
    reason: str | None


class AutomationControlRepository(Protocol):
    async def get(self) -> AutomationState: ...

    async def set(self, state: AutomationState) -> None: ...


class AutomationControlService:
    def __init__(
        self,
        repository: AutomationControlRepository,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or SystemClock()

    async def status(self) -> AutomationState:
        return await self._repository.get()

    async def pause(self, *, reason: str) -> AutomationState:
        normalized = reason.strip()
        if not normalized:
            raise ValueError("pause reason cannot be blank")
        state = AutomationState(
            paused=True,
            updated_at=self._clock.now(),
            reason=normalized[:500],
        )
        await self._repository.set(state)
        return state

    async def resume(self) -> AutomationState:
        state = AutomationState(
            paused=False,
            updated_at=self._clock.now(),
            reason=None,
        )
        await self._repository.set(state)
        return state
