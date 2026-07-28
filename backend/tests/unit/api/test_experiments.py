from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.experiments import (
    ExperimentRunDetail,
    ExperimentRunNotFoundError,
    ExperimentRunPage,
    ListExperimentRuns,
    ReplayDatasetSummary,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.experiments import ExperimentRunStatus

NOW = datetime(2026, 1, 1, tzinfo=UTC)
RUN_ID = UUID("00000000-0000-4000-8000-000000000101")


class StubExperimentService:
    def __init__(self) -> None:
        self.query: ListExperimentRuns | None = None

    async def list(self, query: ListExperimentRuns) -> ExperimentRunPage:
        self.query = query
        return ExperimentRunPage(
            items=(detail(),),
            page=query.page,
            page_size=query.page_size,
            total=1,
        )

    async def get(self, run_id: UUID) -> ExperimentRunDetail:
        if run_id != RUN_ID:
            raise ExperimentRunNotFoundError(str(run_id))
        return detail()


class StubDatasetService:
    def list(self) -> tuple[ReplayDatasetSummary, ...]:
        return (
            ReplayDatasetSummary(
                dataset_id="synthetic-lab",
                version="1.0.0",
                schema_version="1",
                created_at=NOW,
                description="Datos sintéticos.",
                content_sha256="a" * 64,
                replay_start=NOW,
                replay_end=NOW,
                market_count=20,
                observation_count=80,
            ),
        )


def detail() -> ExperimentRunDetail:
    return ExperimentRunDetail(
        experiment_run_id=RUN_ID,
        dataset_id="synthetic-lab",
        dataset_version="1.0.0",
        started_at=NOW,
        finished_at=NOW,
        status=ExperimentRunStatus.COMPLETED,
        replay_start=NOW,
        replay_end=NOW,
        random_seed=0,
        configuration_hash="a" * 64,
        code_version=None,
        result_hash="b" * 64,
        correlation_id="experiment-test",
        safe_error_type=None,
        reproducible=True,
    )


def create_test_app():
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
        )
    )
    application.state.experiment_run_query_service = StubExperimentService()
    application.state.replay_dataset_query_service = StubDatasetService()
    return application


@pytest.mark.asyncio
async def test_experiment_routes_and_dataset_catalog() -> None:
    application = create_test_app()
    service = application.state.experiment_run_query_service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        listing = await client.get(
            "/experiment-runs",
            params={"dataset": "synthetic-lab", "status": "completed"},
        )
        run = await client.get(f"/experiment-runs/{RUN_ID}")
        datasets = await client.get("/replay-datasets")

    assert listing.status_code == 200
    assert listing.json()["items"][0]["reproducible"] is True
    assert run.status_code == 200
    assert run.json()["result_hash"] == "b" * 64
    assert datasets.status_code == 200
    assert datasets.json()[0]["observation_count"] == 80
    assert service.query.dataset_id == "synthetic-lab"
    assert service.query.status is ExperimentRunStatus.COMPLETED


def test_openapi_includes_replay_routes() -> None:
    schema = create_test_app().openapi()

    assert "/experiment-runs" in schema["paths"]
    assert "/experiment-runs/{run_id}" in schema["paths"]
    assert "/replay-datasets" in schema["paths"]
