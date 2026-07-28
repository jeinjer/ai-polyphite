"""Small cooperative rate limiter for the public Manifold API."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from math import isfinite
from time import monotonic

type AsyncSleep = Callable[[float], Awaitable[None]]
type MonotonicClock = Callable[[], float]


class RequestRateLimiter:
    """Space requests so one process stays below the configured per-minute limit."""

    def __init__(
        self,
        requests_per_minute: int,
        *,
        sleep: AsyncSleep = asyncio.sleep,
        clock: MonotonicClock = monotonic,
    ) -> None:
        if not 1 <= requests_per_minute <= 500:
            raise ValueError("requests_per_minute must be between 1 and 500.")
        self._interval_seconds = 60 / requests_per_minute
        if not isfinite(self._interval_seconds):
            raise ValueError("Rate-limit interval must be finite.")
        self._sleep = sleep
        self._clock = clock
        self._next_request_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            delay = max(0.0, self._next_request_at - now)
            if delay:
                await self._sleep(delay)
                now = self._clock()
            self._next_request_at = max(self._next_request_at, now) + (self._interval_seconds)
