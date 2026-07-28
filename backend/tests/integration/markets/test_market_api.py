from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.markets.commands import (
    CreateMarket,
    CreateProvider,
    RecordMarketObservation,
    RecordMarketSnapshot,
)
from predictionlab.application.markets.services import (
    MarketObservationService,
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

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def create_context(settings: Settings):
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    dependencies = ServiceDependencies(
        unit_of_work=unit_of_work,
        clock=lambda: NOW,
        id_factory=uuid4,
    )
    return engine, session_factory, dependencies


async def cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    provider_id: UUID,
    market_ids: tuple[UUID, ...],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(MarketSnapshotModel).where(MarketSnapshotModel.market_id.in_(market_ids))
        )
        await session.execute(
            delete(MarketObservationModel).where(MarketObservationModel.market_id.in_(market_ids))
        )
        await session.execute(
            delete(MarketStateChangeModel).where(MarketStateChangeModel.market_id.in_(market_ids))
        )
        await session.execute(delete(MarketModel).where(MarketModel.market_id.in_(market_ids)))
        await session.execute(delete(ProviderModel).where(ProviderModel.provider_id == provider_id))
        await session.commit()


async def record_snapshot(
    service: MarketSnapshotService,
    market_id: UUID,
    *,
    observed_at: datetime,
    yes_price: str,
) -> None:
    await service.record(
        RecordMarketSnapshot(
            market_id=market_id,
            observed_at=observed_at,
            yes_price=Decimal(yes_price),
            no_price=Decimal("0.40"),
            probability=Decimal(yes_price),
            spread=Decimal("0.02"),
            volume=Decimal("100"),
            liquidity=Decimal("50"),
        )
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_api_queries_real_postgres_with_observability() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )
    engine, session_factory, dependencies = create_context(settings)
    provider_id: UUID | None = None
    market_ids: tuple[UUID, ...] = ()

    try:
        provider = await ProviderService(dependencies).create(
            CreateProvider(
                code=f"provider_{uuid4().hex}",
                name="API Test Provider",
            )
        )
        provider_id = provider.provider_id
        alpha = await MarketService(dependencies).create(
            CreateMarket(
                provider_id=provider.provider_id,
                provider_market_id="alpha",
                title="Alpha market",
                category="science",
                status=MarketStatus.OPEN,
            )
        )
        beta = await MarketService(dependencies).create(
            CreateMarket(
                provider_id=provider.provider_id,
                provider_market_id="beta",
                title="Beta market",
                category="science",
                status=MarketStatus.OPEN,
            )
        )
        gamma = await MarketService(dependencies).create(
            CreateMarket(
                provider_id=provider.provider_id,
                provider_market_id="gamma",
                title="Gamma market",
                category="politics",
                status=MarketStatus.CLOSED,
            )
        )
        market_ids = (alpha.market_id, beta.market_id, gamma.market_id)
        snapshot_service = MarketSnapshotService(dependencies)
        await record_snapshot(
            snapshot_service,
            beta.market_id,
            observed_at=NOW + timedelta(minutes=1),
            yes_price="0.60",
        )
        await record_snapshot(
            snapshot_service,
            beta.market_id,
            observed_at=NOW + timedelta(minutes=2),
            yes_price="0.65",
        )
        observation_service = MarketObservationService(dependencies)
        await observation_service.record(
            RecordMarketObservation(
                market_id=beta.market_id,
                observed_at=NOW + timedelta(minutes=1),
                provider_code=provider.code,
                probability=Decimal("0.60"),
                volume=Decimal("100"),
                liquidity=None,
                source_updated_at=NOW,
                raw_payload_hash="a" * 64,
            )
        )
        await observation_service.record(
            RecordMarketObservation(
                market_id=beta.market_id,
                observed_at=NOW + timedelta(minutes=2),
                provider_code=provider.code,
                probability=Decimal("0.65"),
                volume=None,
                liquidity=None,
                source_updated_at=NOW + timedelta(minutes=1),
                raw_payload_hash="b" * 64,
            )
        )

        application = create_app(settings)
        async with application.router.lifespan_context(application):
            transport = httpx.ASGITransport(app=application)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                first_page = await client.get(
                    "/markets",
                    params={
                        "page": 1,
                        "page_size": 1,
                        "status": "open",
                        "provider": provider.code,
                        "category": "science",
                        "order_by": "title",
                        "direction": "asc",
                    },
                )
                second_page = await client.get(
                    "/markets",
                    params={
                        "page": 2,
                        "page_size": 1,
                        "status": "open",
                        "provider": provider.code,
                        "category": "science",
                        "order_by": "title",
                        "direction": "asc",
                    },
                )
                detail = await client.get(
                    f"/markets/{beta.market_id}",
                    headers={"X-Correlation-ID": "market-detail-123"},
                )
                missing = await client.get(f"/markets/{uuid4()}")
                observations = await client.get(
                    f"/markets/{beta.market_id}/observations",
                    params={"page": 1, "page_size": 1},
                )
                history = await client.get(
                    f"/markets/{beta.market_id}/history",
                    params={"page_size": 20},
                )

        assert first_page.status_code == 200
        assert first_page.json()["total"] == 2
        assert first_page.json()["pages"] == 2
        assert first_page.json()["items"][0]["title"] == "Alpha market"
        assert second_page.json()["items"][0]["title"] == "Beta market"
        assert detail.status_code == 200
        assert detail.headers["x-correlation-id"] == "market-detail-123"
        assert detail.json()["latest_snapshot"]["yes_price"] == "0.6500000000"
        assert detail.json()["latest_observation"]["probability"] == "0.6500000000"
        assert detail.json()["latest_observation"]["volume"] is None
        assert detail.json()["probability_change"] == "0.0500000000"
        assert missing.status_code == 404
        assert observations.status_code == 200
        assert observations.json()["total"] == 2
        assert len(observations.json()["items"]) == 1
        assert observations.json()["items"][0]["volume"] is None
        assert history.status_code == 200
        assert "observation" in {item["event_type"] for item in history.json()["items"]}

        metrics = application.state.request_metrics.snapshot()
        list_metric = next(
            metric for metric in metrics if metric.route == "/markets" and metric.status_code == 200
        )
        detail_metric = next(
            metric
            for metric in metrics
            if metric.route == "/markets/{market_id}" and metric.status_code == 200
        )
        missing_metric = next(
            metric
            for metric in metrics
            if metric.route == "/markets/{market_id}" and metric.status_code == 404
        )
        assert list_metric.request_count == 2
        assert detail_metric.request_count == 1
        assert missing_metric.request_count == 1
    finally:
        if provider_id is not None and market_ids:
            await cleanup(
                session_factory,
                provider_id=provider_id,
                market_ids=market_ids,
            )
        await engine.dispose()
