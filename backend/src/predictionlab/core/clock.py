"""Explicit clocks for wall-time and deterministic replay."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Source of timezone-aware UTC time."""

    def now(self) -> datetime: ...

    def __call__(self) -> datetime: ...


class SystemClock:
    """Production wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def __call__(self) -> datetime:
        return self.now()


class ReplayClock:
    """Monotonic simulated clock over a fixed event schedule."""

    def __init__(
        self,
        *,
        start_at: datetime,
        event_times: Iterable[datetime] = (),
    ) -> None:
        self._start_at = _utc(start_at, "start_at")
        normalized_events = sorted({_utc(value, "event_time") for value in event_times})
        if normalized_events and normalized_events[0] < self._start_at:
            raise ValueError("event_times cannot precede start_at")
        self._event_times = tuple(normalized_events)
        self.reset()

    @property
    def start_at(self) -> datetime:
        return self._start_at

    @property
    def event_times(self) -> tuple[datetime, ...]:
        return self._event_times

    @property
    def next_event_at(self) -> datetime | None:
        if self._next_event_index >= len(self._event_times):
            return None
        return self._event_times[self._next_event_index]

    def now(self) -> datetime:
        return self._current

    def __call__(self) -> datetime:
        return self.now()

    def advance_to_next(self) -> datetime | None:
        next_event = self.next_event_at
        if next_event is None:
            return None
        self._current = next_event
        self._next_event_index += 1
        return self._current

    def advance(self, duration: timedelta) -> datetime:
        if duration < timedelta(0):
            raise ValueError("ReplayClock cannot move backwards")
        return self.advance_until(self._current + duration)

    def advance_until(self, target: datetime) -> datetime:
        normalized_target = _utc(target, "target")
        if normalized_target < self._current:
            raise ValueError("ReplayClock cannot move backwards")
        self._current = normalized_target
        while (
            self._next_event_index < len(self._event_times)
            and self._event_times[self._next_event_index] <= normalized_target
        ):
            self._next_event_index += 1
        return self._current

    def reset(self) -> datetime:
        self._current = self._start_at
        self._next_event_index = 0
        return self._current


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)
