from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.automation import AutomationControlService, AutomationState
from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)
from predictionlab.application.collectors.service import (
    CollectorRunNotFoundError,
)
from predictionlab.application.sources import SourceHealthItem
from predictionlab.collectors import CollectorRunStatus
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def run_detail(run_id: UUID) -> CollectorRunDetail:
    return CollectorRunDetail(
        run_id=run_id,
        provider_code="mock",
        started_at=NOW,
        finished_at=NOW,
        status=CollectorRunStatus.COMPLETED,
        markets_fetched=3,
        markets_created=2,
        markets_updated=1,
        markets_unchanged=0,
        observations_fetched=3,
        observations_created=2,
        observations_duplicated=1,
        observations_skipped=0,
        retry_count=0,
        duration_ms=12.5,
        safe_error_type=None,
        correlation_id="correlation-1",
    )


class StubCollectorRunService:
    def __init__(self, run: CollectorRunDetail | None) -> None:
        self.run = run
        self.query: ListCollectorRuns | None = None

    async def list(self, query: ListCollectorRuns) -> CollectorRunPage:
        self.query = query
        items = (self.run,) if self.run is not None else ()
        return CollectorRunPage(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=len(items),
        )

    async def get(self, run_id: UUID) -> CollectorRunDetail:
        if self.run is None or self.run.run_id != run_id:
            raise CollectorRunNotFoundError(str(run_id))
        return self.run


class StubSourceHealthService:
    async def list(self) -> tuple[SourceHealthItem, ...]:
        return (
            SourceHealthItem(
                code="mock",
                name="Fuente simulada",
                status="healthy",
                checked_at=NOW,
                latency_ms=1.25,
                safe_error_type=None,
            ),
        )


class MemoryAutomationRepository:
    def __init__(self) -> None:
        self.state = AutomationState(paused=False, updated_at=None, reason=None)

    async def get(self) -> AutomationState:
        return self.state

    async def set(self, state: AutomationState) -> None:
        self.state = state


def create_test_app():
    return create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
        )
    )


@pytest.mark.asyncio
async def test_collector_run_routes_filter_and_return_safe_audit_data() -> None:
    run = run_detail(uuid4())
    service = StubCollectorRunService(run)
    application = create_test_app()
    application.state.collector_run_query_service = service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/collector-runs",
            params={
                "provider": "mock",
                "status": "completed",
                "page_size": 5,
            },
        )
        detail_response = await client.get(f"/collector-runs/{run.run_id}")

    assert response.status_code == 200
    assert response.json()["items"][0]["safe_error_type"] is None
    assert detail_response.status_code == 200
    assert detail_response.json()["correlation_id"] == "correlation-1"
    assert service.query is not None
    assert service.query.provider_code == "mock"
    assert service.query.status is CollectorRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_source_health_route_exposes_only_configured_source_status() -> None:
    application = create_test_app()
    application.state.source_health_service = StubSourceHealthService()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/sources")

    assert response.status_code == 200
    assert response.json() == [
        {
            "code": "mock",
            "name": "Fuente simulada",
            "status": "healthy",
            "checked_at": "2026-07-28T12:00:00Z",
            "latency_ms": 1.25,
            "safe_error_type": None,
        }
    ]


@pytest.mark.asyncio
async def test_operator_can_pause_and_resume_automation_through_api() -> None:
    application = create_test_app()
    application.state.automation_control_service = AutomationControlService(
        MemoryAutomationRepository()
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        initial = await client.get("/automation")
        paused = await client.post(
            "/automation/pause",
            json={"reason": "operator test"},
        )
        resumed = await client.post("/automation/resume")

    assert initial.json()["paused"] is False
    assert paused.json()["paused"] is True
    assert paused.json()["reason"] == "operator test"
    assert resumed.json()["paused"] is False


def test_openapi_documents_historical_and_operational_routes() -> None:
    schema = create_test_app().openapi()

    assert "/markets/{market_id}/observations" in schema["paths"]
    assert "/markets/{market_id}/history" in schema["paths"]
    assert "/collector-runs" in schema["paths"]
    assert "/collector-runs/{run_id}" in schema["paths"]
    assert "/sources" in schema["paths"]
    assert "/automation" in schema["paths"]
    assert "/automation/pause" in schema["paths"]
    assert "/automation/resume" in schema["paths"]
