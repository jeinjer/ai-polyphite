from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from predictionlab.application.markets.errors import MarketNotFoundError
from predictionlab.application.markets.queries import (
    ListMarkets,
    MarketDetail,
    MarketPage,
    ProviderSummary,
)
from predictionlab.application.markets.query_service import MarketQueryService
from predictionlab.domain.markets import MarketStatus

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def detail(market_id: UUID) -> MarketDetail:
    return MarketDetail(
        market_id=market_id,
        provider_market_id="external-1",
        title="Market",
        description="Description",
        category="science",
        resolution_at=None,
        source_created_at=NOW,
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
        provider=ProviderSummary(uuid4(), "provider", "Provider", True),
        latest_snapshot=None,
    )


class StubReadRepository:
    def __init__(self, market: MarketDetail | None) -> None:
        self.market = market
        self.list_query: ListMarkets | None = None

    async def list(self, query: ListMarkets) -> MarketPage:
        self.list_query = query
        return MarketPage(items=(), page=query.page, page_size=query.page_size, total=21)

    async def get(self, market_id: UUID) -> MarketDetail | None:
        if self.market is not None and self.market.market_id == market_id:
            return self.market
        return None


@pytest.mark.asyncio
async def test_list_query_returns_pagination_metadata() -> None:
    repository = StubReadRepository(None)
    service = MarketQueryService(repository)
    query = ListMarkets(page=2, page_size=10, status=MarketStatus.OPEN)

    result = await service.list(query)

    assert repository.list_query == query
    assert result.page == 2
    assert result.total == 21
    assert result.pages == 3


@pytest.mark.asyncio
async def test_detail_query_raises_typed_not_found_error() -> None:
    service = MarketQueryService(StubReadRepository(None))

    with pytest.raises(MarketNotFoundError):
        await service.get(uuid4())


@pytest.mark.parametrize(
    ("page", "page_size"),
    [(0, 20), (1, 0), (1, 101)],
)
def test_list_query_rejects_invalid_pagination(page: int, page_size: int) -> None:
    with pytest.raises(ValueError):
        ListMarkets(page=page, page_size=page_size)
