from __future__ import annotations

from datetime import UTC, datetime

import pytest

from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    ProviderError,
    ProviderHealthStatus,
    ProviderMarketNotFoundError,
    ProviderMarketStatus,
    ProviderUnavailableError,
)
from predictionlab.providers.defaults import create_default_provider_registry
from predictionlab.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_supports_catalog_filters_and_cursor_pagination() -> None:
    provider = MockProvider()

    first_page = await provider.fetch_markets(FetchMarketsRequest(limit=2))
    second_page = await provider.fetch_markets(
        FetchMarketsRequest(limit=2, cursor=first_page.next_cursor)
    )
    resolved = await provider.fetch_markets(
        FetchMarketsRequest(statuses=frozenset({ProviderMarketStatus.RESOLVED}))
    )
    updated = await provider.fetch_markets(
        FetchMarketsRequest(
            updated_after=datetime(2026, 2, 1, tzinfo=UTC),
        )
    )

    assert len(first_page.markets) == 2
    assert first_page.next_cursor == "mock:2"
    assert len(second_page.markets) == 1
    assert second_page.next_cursor is None
    assert [market.provider_market_id for market in resolved.markets] == ["mock-space-launch"]
    assert [market.provider_market_id for market in updated.markets] == ["mock-space-launch"]


@pytest.mark.asyncio
async def test_mock_provider_serves_detail_and_snapshot_history() -> None:
    provider = MockProvider()

    market = await provider.fetch_market("mock-ai-2027")
    missing_market = await provider.fetch_market("missing")
    latest = await provider.fetch_latest_snapshot("mock-ai-2027")
    first_snapshot = await provider.fetch_snapshots(
        FetchSnapshotsRequest(provider_market_id="mock-ai-2027", limit=1)
    )
    second_snapshot = await provider.fetch_snapshots(
        FetchSnapshotsRequest(
            provider_market_id="mock-ai-2027",
            limit=1,
            cursor=first_snapshot.next_cursor,
        )
    )

    assert market is not None
    assert market.title.startswith("Will a frontier AI")
    assert missing_market is None
    assert latest is not None
    assert latest.probability == second_snapshot.snapshots[0].probability
    assert first_snapshot.next_cursor == "mock:1"
    assert second_snapshot.next_cursor is None

    with pytest.raises(ProviderMarketNotFoundError):
        await provider.fetch_latest_snapshot("missing")


@pytest.mark.asyncio
async def test_mock_provider_health_and_failure_modes_are_deterministic() -> None:
    healthy = MockProvider()
    unavailable = MockProvider(available=False)

    healthy_result = await healthy.health_check()
    unhealthy_result = await unavailable.health_check()

    assert healthy_result.status is ProviderHealthStatus.HEALTHY
    assert healthy_result.error_type is None
    assert unhealthy_result.status is ProviderHealthStatus.UNHEALTHY
    assert unhealthy_result.error_type == "ProviderUnavailableError"

    with pytest.raises(ProviderUnavailableError):
        await unavailable.fetch_markets(FetchMarketsRequest())
    with pytest.raises(ProviderError, match="cursor"):
        await healthy.fetch_markets(FetchMarketsRequest(cursor="invalid:1"))


def test_default_registry_contains_only_mock_provider() -> None:
    registry = create_default_provider_registry()

    assert registry.registered_codes == ("mock",)
    assert isinstance(registry.create("mock"), MockProvider)
