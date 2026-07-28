from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from predictionlab.core.clock import ReplayClock, SystemClock

START = datetime(2026, 1, 1, tzinfo=UTC)


def test_system_clock_returns_utc() -> None:
    assert SystemClock().now().tzinfo is UTC


def test_replay_clock_steps_advances_and_resets_deterministically() -> None:
    events = (START, START + timedelta(hours=1), START + timedelta(hours=2))
    clock = ReplayClock(start_at=START, event_times=reversed(events))

    assert clock.now() == START
    assert clock.advance_to_next() == START
    assert clock.advance_to_next() == events[1]
    assert clock.advance(timedelta(minutes=30)) == events[1] + timedelta(minutes=30)
    assert clock.next_event_at == events[2]
    assert clock.reset() == START
    assert clock.next_event_at == START


def test_replay_clock_prevents_temporal_rollbacks() -> None:
    clock = ReplayClock(start_at=START)

    with pytest.raises(ValueError, match="backwards"):
        clock.advance(timedelta(seconds=-1))
    with pytest.raises(ValueError, match="backwards"):
        clock.advance_until(START - timedelta(seconds=1))
