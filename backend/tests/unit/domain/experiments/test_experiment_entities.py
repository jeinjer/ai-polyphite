from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from predictionlab.domain.experiments import (
    ExperimentInvariantError,
    ExperimentRun,
    ExperimentRunStatus,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
HASH = "a" * 64


def running_experiment() -> ExperimentRun:
    return ExperimentRun(
        experiment_run_id=uuid4(),
        dataset_id="synthetic-lab",
        dataset_version="1.0.0",
        started_at=NOW,
        finished_at=None,
        status=ExperimentRunStatus.RUNNING,
        replay_start=NOW,
        replay_end=NOW,
        random_seed=7,
        configuration_hash=HASH,
        code_version=None,
        result_hash=None,
        correlation_id="test",
        safe_error_type=None,
    )


def test_experiment_completes_as_reproducible() -> None:
    completed = running_experiment().complete(
        finished_at=NOW + timedelta(seconds=1),
        replay_end=NOW + timedelta(days=1),
        result_hash="b" * 64,
    )

    assert completed.status is ExperimentRunStatus.COMPLETED
    assert completed.reproducible is True


def test_experiment_failure_keeps_only_safe_error_type() -> None:
    failed = running_experiment().fail(
        finished_at=NOW + timedelta(seconds=1),
        replay_end=NOW,
        safe_error_type="ReplayDatasetIntegrityError",
    )

    assert failed.status is ExperimentRunStatus.FAILED
    assert failed.safe_error_type == "ReplayDatasetIntegrityError"
    assert failed.result_hash is None


def test_experiment_rejects_invalid_hash() -> None:
    with pytest.raises(ExperimentInvariantError, match="configuration_hash"):
        replace(running_experiment(), configuration_hash="invalid")
