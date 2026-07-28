from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.markets.errors import MarketNotFoundError
from predictionlab.application.markets.queries import (
    ListMarkets,
    MarketDetail,
    MarketPage,
    MarketSummary,
    ProviderSummary,
    SnapshotSummary,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.markets import MarketStatus

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def market_detail(market_id: UUID) -> MarketDetail:
    return MarketDetail(
        market_id=market_id,
        provider_market_id="external-1",
        title="Will the API work?",
        description="Read-only market detail.",
        category="engineering",
        resolution_at=None,
        source_created_at=NOW,
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
        provider=ProviderSummary(uuid4(), "provider", "Provider", True),
        latest_snapshot=SnapshotSummary(
            snapshot_id=uuid4(),
            observed_at=NOW,
            yes_price=Decimal("0.61"),
            no_price=Decimal("0.42"),
            probability=Decimal("0.60"),
            spread=Decimal("0.03"),
            volume=Decimal("100"),
            liquidity=Decimal("50"),
        ),
    )


def summary(detail: MarketDetail) -> MarketSummary:
    return MarketSummary(
        market_id=detail.market_id,
        provider_market_id=detail.provider_market_id,
        title=detail.title,
        category=detail.category,
        resolution_at=detail.resolution_at,
        source_created_at=detail.source_created_at,
        status=detail.status,
        ingested_at=detail.ingested_at,
        updated_at=detail.updated_at,
        provider=detail.provider,
        latest_snapshot=detail.latest_snapshot,
    )


class StubMarketQueryService:
    def __init__(self, market: MarketDetail | None) -> None:
        self.market = market
        self.list_query: ListMarkets | None = None

    async def list(self, query: ListMarkets) -> MarketPage:
        self.list_query = query
        items = (summary(self.market),) if self.market is not None else ()
        return MarketPage(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=len(items),
        )

    async def get(self, market_id: UUID) -> MarketDetail:
        if self.market is None or self.market.market_id != market_id:
            raise MarketNotFoundError(str(market_id))
        return self.market


def create_test_app(service: StubMarketQueryService):
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
        )
    )
    application.state.market_query_service = service
    return application


@pytest.mark.asyncio
async def test_list_markets_maps_filters_pagination_and_response() -> None:
    detail = market_detail(uuid4())
    service = StubMarketQueryService(detail)
    application = create_test_app(service)
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/markets",
            params={
                "page": 2,
                "page_size": 5,
                "status": "open",
                "provider": "provider",
                "category": "engineering",
                "order_by": "title",
                "direction": "asc",
            },
            headers={"X-Correlation-ID": "query-123"},
        )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "query-123"
    assert response.json()["items"][0]["market_id"] == str(detail.market_id)
    assert response.json()["items"][0]["latest_snapshot"]["yes_price"] == "0.61"
    assert service.list_query == ListMarkets(
        page=2,
        page_size=5,
        status=MarketStatus.OPEN,
        provider_code="provider",
        category="engineering",
        order_by="title",
        direction="asc",
    )


@pytest.mark.asyncio
async def test_get_market_returns_detail_and_normalized_metrics() -> None:
    detail = market_detail(uuid4())
    application = create_test_app(StubMarketQueryService(detail))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/markets/{detail.market_id}")

    metric = application.state.request_metrics.snapshot()[0]
    assert response.status_code == 200
    assert response.json()["description"] == detail.description
    assert metric.route == "/markets/{market_id}"
    assert metric.status_code == 200


@pytest.mark.asyncio
async def test_get_market_returns_documented_404() -> None:
    application = create_test_app(StubMarketQueryService(None))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/markets/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Market not found."}


def test_openapi_documents_market_operations_and_filters() -> None:
    schema = create_test_app(StubMarketQueryService(None)).openapi()

    assert schema["paths"]["/markets"]["get"]["operationId"] == "list_markets"
    assert schema["paths"]["/markets/{market_id}"]["get"]["operationId"] == "get_market"
    parameter_names = {
        parameter["name"] for parameter in schema["paths"]["/markets"]["get"]["parameters"]
    }
    assert {
        "page",
        "page_size",
        "status",
        "provider",
        "category",
        "order_by",
        "direction",
    } <= parameter_names
