from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.markets.commands import (
    CreateMarket,
    CreateProvider,
    RecordMarketSnapshot,
)
from predictionlab.application.markets.services import (
    MarketService,
    MarketSnapshotService,
    ProviderService,
    ServiceDependencies,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.markets import MarketStatus
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.providers.base import FetchMarketsRequest, ProviderHealthStatus
from predictionlab.providers.defaults import create_default_provider_registry

CREATED_AT = datetime(2025, 12, 31, tzinfo=UTC)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_provider_data_reaches_existing_market_api() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    dependencies = ServiceDependencies(
        unit_of_work=unit_of_work,
        clock=lambda: CREATED_AT,
        id_factory=uuid4,
    )
    provider_id: UUID | None = None
    market_ids: list[UUID] = []

    try:
        sdk_provider = create_default_provider_registry().create("mock")
        health = await sdk_provider.health_check()
        assert health.status is ProviderHealthStatus.HEALTHY

        external_markets = []
        cursor: str | None = None
        while True:
            batch = await sdk_provider.fetch_markets(FetchMarketsRequest(cursor=cursor, limit=2))
            external_markets.extend(batch.markets)
            cursor = batch.next_cursor
            if cursor is None:
                break

        persisted_provider = await ProviderService(dependencies).create(
            CreateProvider(
                code=f"mock_{uuid4().hex[:12]}",
                name=sdk_provider.name,
            )
        )
        provider_id = persisted_provider.provider_id
        market_service = MarketService(dependencies)
        snapshot_service = MarketSnapshotService(dependencies)

        for external_market in external_markets:
            market = await market_service.create(
                CreateMarket(
                    provider_id=persisted_provider.provider_id,
                    provider_market_id=external_market.provider_market_id,
                    title=external_market.title,
                    description=external_market.description,
                    category=external_market.category,
                    resolution_at=external_market.resolution_at,
                    status=MarketStatus(external_market.status.value),
                )
            )
            market_ids.append(market.market_id)
            external_snapshot = await sdk_provider.fetch_latest_snapshot(
                external_market.provider_market_id
            )
            if external_snapshot is not None:
                assert external_snapshot.yes_price is not None
                assert external_snapshot.no_price is not None
                assert external_snapshot.probability is not None
                assert external_snapshot.spread is not None
                assert external_snapshot.volume is not None
                assert external_snapshot.liquidity is not None
                await snapshot_service.record(
                    RecordMarketSnapshot(
                        market_id=market.market_id,
                        observed_at=external_snapshot.observed_at,
                        yes_price=external_snapshot.yes_price,
                        no_price=external_snapshot.no_price,
                        probability=external_snapshot.probability,
                        spread=external_snapshot.spread,
                        volume=external_snapshot.volume,
                        liquidity=external_snapshot.liquidity,
                    )
                )

        application = create_app(settings)
        async with application.router.lifespan_context(application):
            transport = httpx.ASGITransport(app=application)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.get(
                    "/markets",
                    params={
                        "provider": persisted_provider.code,
                        "page_size": 10,
                        "order_by": "title",
                        "direction": "asc",
                    },
                )
                detail = await client.get(f"/markets/{market_ids[0]}")

        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert detail.status_code == 200
        assert detail.json()["provider"]["code"] == persisted_provider.code
        assert detail.json()["latest_snapshot"] is not None
    finally:
        if provider_id is not None:
            await _cleanup(
                session_factory,
                provider_id=provider_id,
                market_ids=tuple(market_ids),
            )
        await engine.dispose()


async def _cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    provider_id: UUID,
    market_ids: tuple[UUID, ...],
) -> None:
    async with session_factory() as session:
        if market_ids:
            await session.execute(
                delete(MarketSnapshotModel).where(MarketSnapshotModel.market_id.in_(market_ids))
            )
            await session.execute(
                delete(MarketObservationModel).where(
                    MarketObservationModel.market_id.in_(market_ids)
                )
            )
            await session.execute(
                delete(MarketStateChangeModel).where(
                    MarketStateChangeModel.market_id.in_(market_ids)
                )
            )
            await session.execute(delete(MarketModel).where(MarketModel.market_id.in_(market_ids)))
        await session.execute(delete(ProviderModel).where(ProviderModel.provider_id == provider_id))
        await session.commit()
