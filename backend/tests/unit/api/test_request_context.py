from __future__ import annotations

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.core.context import get_correlation_id, get_trace_id
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings


def create_test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )


@pytest.mark.asyncio
async def test_request_context_propagates_correlation_and_trace_ids() -> None:
    application = create_app(create_test_settings())
    incoming_trace_id = "a" * 32
    incoming_span_id = "b" * 16
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/health/live",
            headers={
                "X-Correlation-ID": "workflow-123",
                "traceparent": f"00-{incoming_trace_id}-{incoming_span_id}-01",
            },
        )

    response_traceparent = response.headers["traceparent"].split("-")
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "workflow-123"
    assert response_traceparent[0] == "00"
    assert response_traceparent[1] == incoming_trace_id
    assert response_traceparent[2] != incoming_span_id
    assert response_traceparent[3] == "01"
    assert get_correlation_id() is None
    assert get_trace_id() is None


@pytest.mark.asyncio
async def test_request_context_replaces_invalid_headers() -> None:
    application = create_app(create_test_settings())
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/health/live",
            headers={
                "X-Correlation-ID": "x" * 129,
                "traceparent": "invalid",
            },
        )

    traceparent = response.headers["traceparent"]
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] != "x" * 129
    assert len(response.headers["x-correlation-id"]) == 36
    assert len(traceparent.split("-")[1]) == 32
