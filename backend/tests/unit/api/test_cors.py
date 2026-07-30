from __future__ import annotations

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.collectors import CollectorRunPage
from predictionlab.application.experiments import ExperimentRunPage
from predictionlab.application.markets import MarketPage
from predictionlab.application.predictions import (
    PredictionListPage,
    PredictionRunPage,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings

ALLOWED_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)
READ_ENDPOINTS = (
    "/markets",
    "/predictions",
    "/sources",
    "/collector-runs",
    "/experiment-runs",
    "/replay-datasets",
)


class EmptyMarketQueryService:
    async def list(self, query):
        return MarketPage((), query.page, query.page_size, 0)


class EmptyPredictionQueryService:
    async def list(self, query):
        return PredictionRunPage((), query.page, query.page_size, 0)

    async def list_summary(self, query):
        return PredictionListPage(
            (),
            query.page,
            query.page_size,
            0,
            {},
        )


class EmptySourceHealthService:
    async def list(self):
        return ()


class EmptyCollectorRunQueryService:
    async def list(self, query):
        return CollectorRunPage((), query.page, query.page_size, 0)


class EmptyExperimentRunQueryService:
    async def list(self, query):
        return ExperimentRunPage((), query.page, query.page_size, 0)


class EmptyReplayDatasetQueryService:
    def list(self):
        return ()


def cors_test_app():
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
            cors_allowed_origins=ALLOWED_ORIGINS,
        )
    )
    application.state.market_query_service = EmptyMarketQueryService()
    application.state.prediction_query_service = EmptyPredictionQueryService()
    application.state.source_health_service = EmptySourceHealthService()
    application.state.collector_run_query_service = EmptyCollectorRunQueryService()
    application.state.experiment_run_query_service = EmptyExperimentRunQueryService()
    application.state.replay_dataset_query_service = EmptyReplayDatasetQueryService()
    return application


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
async def test_allowed_origins_receive_cors_header_on_dashboard_reads(
    origin: str,
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cors_test_app()),
        base_url="http://testserver",
    ) as client:
        for endpoint in READ_ENDPOINTS:
            response = await client.get(endpoint, headers={"Origin": origin})

            assert response.status_code == 200, endpoint
            assert response.headers["access-control-allow-origin"] == origin
            assert response.headers["vary"] == "Origin"


@pytest.mark.asyncio
async def test_disallowed_origin_does_not_receive_cors_permission() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cors_test_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/markets",
            headers={"Origin": "http://malicious.example"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", READ_ENDPOINTS)
async def test_preflight_options_allows_dashboard_gets(endpoint: str) -> None:
    origin = "http://127.0.0.1:3000"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cors_test_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            endpoint,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": ("accept,x-correlation-id,traceparent"),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "x-correlation-id" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.asyncio
async def test_preflight_rejects_disallowed_origin() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cors_test_app()),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/markets",
            headers={
                "Origin": "http://malicious.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
