from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderHealthStatus,
    ProviderMarketStatus,
    ProviderProtocolError,
    ProviderRateLimitError,
    ProviderResolutionOutcome,
    ProviderUnavailableError,
)
from predictionlab.providers.manifold import ManifoldProvider
from predictionlab.providers.manifold.rate_limit import RequestRateLimiter

FIXTURES = Path(__file__).parents[2] / "fixtures" / "manifold"
NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


async def _no_sleep(_: float) -> None:
    return None


def _fixture_response(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/v0/search-markets":
        before_time = request.url.params.get("beforeTime")
        if before_time is None:
            fixture = "markets_page_1.json"
        elif before_time == "1710000001000":
            fixture = "markets_page_2.json"
        else:
            return httpx.Response(
                200,
                content=b"[]",
                headers={"Content-Type": "application/json"},
                request=request,
            )
    else:
        market_id = path.removeprefix("/v0/market/")
        fixture = f"market_{market_id}.json"
    fixture_path = FIXTURES / fixture
    if not fixture_path.exists():
        return httpx.Response(404, request=request)
    return httpx.Response(
        200,
        content=fixture_path.read_bytes(),
        headers={"Content-Type": "application/json"},
        request=request,
    )


def _provider(
    handler: Callable[[httpx.Request], httpx.Response] = _fixture_response,
) -> tuple[ManifoldProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return (
        ManifoldProvider(
            http_client=client,
            clock=lambda: NOW,
            sleep=_no_sleep,
        ),
        client,
    )


@pytest.mark.asyncio
async def test_fetch_markets_filters_incompatible_types_and_paginates() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _fixture_response(request)

    provider, client = _provider(handler)
    try:
        first = await provider.fetch_markets(FetchMarketsRequest(limit=3))
        second = await provider.fetch_markets(
            FetchMarketsRequest(cursor=first.next_cursor, limit=3)
        )
    finally:
        await client.aclose()

    assert [market.provider_market_id for market in first.markets] == ["binary-open"]
    assert first.next_cursor == "manifold:created-time:1710000001000"
    assert first.markets[0].status is ProviderMarketStatus.OPEN
    assert first.markets[0].source_created_at == datetime(
        2024,
        3,
        9,
        16,
        0,
        3,
        tzinfo=UTC,
    )
    assert [market.status for market in second.markets] == [
        ProviderMarketStatus.CLOSED,
        ProviderMarketStatus.RESOLVED,
        ProviderMarketStatus.CANCELLED,
    ]
    assert second.next_cursor == "manifold:created-time:1709000001000"
    assert requests[0].url.host == "api.manifold.markets"
    assert requests[0].url.params["contractType"] == "BINARY"
    assert requests[1].url.params["beforeTime"] == "1710000001000"


@pytest.mark.asyncio
async def test_market_detail_preserves_provenance_and_utc_timestamps() -> None:
    provider, client = _provider()
    try:
        market = await provider.fetch_market("binary-open")
        ignored = await provider.fetch_market("numeric-ignored")
    finally:
        await client.aclose()

    assert market is not None
    assert market.provider_market_id == "binary-open"
    assert market.description == "Sanitized binary market used by AI-Polyphite tests."
    assert market.category == "technology"
    assert market.source_created_at is not None
    assert market.source_created_at.tzinfo is UTC
    assert ignored is None


@pytest.mark.asyncio
async def test_latest_snapshot_keeps_probability_but_does_not_invent_prices() -> None:
    provider, client = _provider()
    try:
        snapshot = await provider.fetch_latest_snapshot("binary-open")
    finally:
        await client.aclose()

    assert snapshot is not None
    assert snapshot.provider_market_id == "binary-open"
    assert snapshot.probability == Decimal("0.625")
    assert snapshot.volume == Decimal("120.5")
    assert snapshot.liquidity == Decimal("45")
    assert snapshot.yes_price is None
    assert snapshot.no_price is None
    assert snapshot.spread is None
    assert snapshot.observed_at.tzinfo is UTC


@pytest.mark.asyncio
async def test_latest_observation_preserves_nullable_provider_metrics() -> None:
    provider, client = _provider()
    try:
        observation = await provider.fetch_latest_observation("binary-open")
    finally:
        await client.aclose()

    assert observation is not None
    assert observation.probability == Decimal("0.625")
    assert observation.volume == Decimal("120.5")
    assert observation.liquidity == Decimal("45")
    assert observation.source_updated_at is not None
    assert observation.observed_at.tzinfo is UTC


@pytest.mark.asyncio
async def test_resolution_mapping_does_not_confuse_close_time_with_outcome() -> None:
    provider, client = _provider()
    try:
        closed = await provider.fetch_market("binary-closed")
        resolved = await provider.fetch_market("binary-resolved")
        cancelled = await provider.fetch_market("binary-cancelled")
    finally:
        await client.aclose()

    assert closed is not None
    assert closed.status is ProviderMarketStatus.CLOSED
    assert closed.resolution_at is not None
    assert closed.resolution_outcome is ProviderResolutionOutcome.UNRESOLVED
    assert closed.resolved_at is None

    assert resolved is not None
    assert resolved.resolution_outcome is ProviderResolutionOutcome.YES
    assert resolved.resolved_at is not None
    assert resolved.resolution_source == "manifold_public_api"

    assert cancelled is not None
    assert cancelled.resolution_outcome is ProviderResolutionOutcome.CANCELLED


@pytest.mark.asyncio
async def test_historical_snapshots_and_incremental_listing_are_not_advertised() -> None:
    provider, client = _provider()
    try:
        with pytest.raises(ProviderCapabilityError):
            await provider.fetch_snapshots(FetchSnapshotsRequest(provider_market_id="binary-open"))
        with pytest.raises(ProviderCapabilityError):
            await provider.fetch_markets(FetchMarketsRequest(updated_after=NOW))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_health_check_uses_public_search_endpoint() -> None:
    provider, client = _provider()
    try:
        health = await provider.health_check()
    finally:
        await client.aclose()

    assert health.status is ProviderHealthStatus.HEALTHY
    assert health.error_type is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (400, ProviderProtocolError),
        (500, ProviderUnavailableError),
    ],
)
async def test_http_failures_are_mapped_to_typed_errors(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    provider, client = _provider(handler)
    try:
        with pytest.raises(expected_error):
            await provider.fetch_markets(FetchMarketsRequest(limit=1))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_rate_limit_error_preserves_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "2.5"},
            request=request,
        )

    provider, client = _provider(handler)
    try:
        with pytest.raises(ProviderRateLimitError) as captured:
            await provider.fetch_markets(FetchMarketsRequest(limit=1))
    finally:
        await client.aclose()

    assert captured.value.retry_after_seconds == 2.5


@pytest.mark.asyncio
async def test_timeout_is_mapped_to_unavailable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("fixture timeout", request=request)

    provider, client = _provider(handler)
    try:
        with pytest.raises(ProviderUnavailableError):
            await provider.fetch_markets(FetchMarketsRequest(limit=1))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_malformed_json_is_a_protocol_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{invalid", request=request)

    provider, client = _provider(handler)
    try:
        with pytest.raises(ProviderProtocolError):
            await provider.fetch_markets(FetchMarketsRequest(limit=1))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_rate_limiter_spaces_requests() -> None:
    current = [0.0]
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)
        current[0] += delay

    limiter = RequestRateLimiter(
        500,
        sleep=sleep,
        clock=lambda: current[0],
    )

    await limiter.acquire()
    await limiter.acquire()

    assert delays == [pytest.approx(0.12)]
