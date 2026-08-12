"""Redis-backed operator control; Redis AOF preserves it across restarts."""

from __future__ import annotations

from datetime import datetime

from redis.asyncio import Redis

from predictionlab.application.automation import AutomationState

_KEY = "ai-polyphite:automation:paper-validation"


class RedisAutomationControlRepository:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self) -> AutomationState:
        values = await self._client.hgetall(_KEY)
        if not values:
            return AutomationState(paused=False, updated_at=None, reason=None)
        updated_at = _text(values.get("updated_at"))
        paused = _text(values.get("paused"))
        reason = _text(values.get("reason"))
        return AutomationState(
            paused=paused == "true",
            updated_at=(datetime.fromisoformat(updated_at) if updated_at else None),
            reason=reason or None,
        )

    async def set(self, state: AutomationState) -> None:
        await self._client.hset(
            _KEY,
            mapping={
                "paused": "true" if state.paused else "false",
                "updated_at": state.updated_at.isoformat() if state.updated_at else "",
                "reason": state.reason or "",
            },
        )


def _text(value: bytes | str | None) -> str | None:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
