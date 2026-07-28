from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from predictionlab.core.clock import ReplayClock
from predictionlab.providers.base import (
    FetchMarketsRequest,
    MarketDataProvider,
    ProviderCapability,
    ProviderHealthStatus,
)
from predictionlab.providers.manifold import ManifoldProvider
from predictionlab.providers.mock import MockProvider
from predictionlab.providers.replay import ReplayProvider, load_replay_dataset

FIXTURES = Path(__file__).parents[1] / "fixtures" / "manifold"
REPLAY_DATASET = (
    Path(__file__).parents[2] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"
)
NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


async def _no_sleep(_: float) -> None:
    return None


def _manifold_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v0/search-markets":
        content = (FIXTURES / "markets_page_1.json").read_bytes()
    else:
        market_id = request.url.path.removeprefix("/v0/market/")
        fixture = FIXTURES / f"market_{market_id}.json"
        if not fixture.exists():
            return httpx.Response(404, request=request)
        content = fixture.read_bytes()
    return httpx.Response(200, content=content, request=request)


@pytest.mark.asyncio
async def test_mock_provider_satisfies_market_data_provider_contract() -> None:
    await _assert_provider_contract(MockProvider(clock=lambda: NOW))


@pytest.mark.asyncio
async def test_manifold_provider_satisfies_market_data_provider_contract() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(_manifold_response)) as client:
        provider = ManifoldProvider(
            http_client=client,
            clock=lambda: NOW,
            sleep=_no_sleep,
        )
        await _assert_provider_contract(provider)


@pytest.mark.asyncio
async def test_replay_provider_satisfies_market_data_provider_contract() -> None:
    dataset = load_replay_dataset(REPLAY_DATASET)
    clock = ReplayClock(
        start_at=dataset.metadata.replay_start,
        event_times=dataset.event_times,
    )
    clock.advance_until(dataset.metadata.replay_end)
    await _assert_provider_contract(ReplayProvider(REPLAY_DATASET, clock=clock))


async def _assert_provider_contract(provider: MarketDataProvider) -> None:
    assert isinstance(provider, MarketDataProvider)
    assert provider.code
    assert provider.name
    assert provider.capabilities.supports(ProviderCapability.MARKET_LISTING)
    assert provider.capabilities.supports(ProviderCapability.MARKET_DETAIL)
    assert provider.capabilities.supports(ProviderCapability.LATEST_OBSERVATION)

    health = await provider.health_check()
    assert health.status is ProviderHealthStatus.HEALTHY
    assert health.checked_at.tzinfo is UTC

    batch = await provider.fetch_markets(FetchMarketsRequest(limit=3))
    assert batch.markets
    market = batch.markets[0]
    assert market.provider_market_id
    assert market.source_created_at is not None
    assert market.source_created_at.tzinfo is UTC

    detail = await provider.fetch_market(market.provider_market_id)
    assert detail is not None
    assert detail.provider_market_id == market.provider_market_id

    observation = await provider.fetch_latest_observation(market.provider_market_id)
    assert observation is not None
    assert observation.provider_market_id == market.provider_market_id
    assert observation.observed_at.tzinfo is UTC
