from datetime import UTC, datetime, timedelta

from predictionlab.runtime.prediction_replay import ReplayPredictionSchedule

START = datetime(2026, 1, 1, tzinfo=UTC)


def test_interval_schedule_releases_only_due_timestamps() -> None:
    schedule = ReplayPredictionSchedule(
        replay_start=START,
        replay_end=START + timedelta(days=2),
        interval=timedelta(days=1),
    )

    assert schedule.due(START - timedelta(seconds=1)) == ()
    assert schedule.due(START) == (START,)
    assert schedule.due(START + timedelta(hours=23)) == ()
    assert schedule.due(START + timedelta(days=2)) == (
        START + timedelta(days=1),
        START + timedelta(days=2),
    )
