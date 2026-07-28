from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.markets.services import ServiceDependencies
from predictionlab.collectors import CollectorConfig, MarketDataCollector
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.collector_state import (
    PostgresProviderCollectionLock,
    SqlAlchemyCollectorCheckpointStore,
    SqlAlchemyCollectorRunStore,
)
from predictionlab.infrastructure.database.models import (
    CollectorCheckpointModel,
    CollectorRunModel,
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.providers.mock import MockProvider

COLLECTOR_CLOCK = datetime(2025, 12, 31, tzinfo=UTC)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_collector_persists_checkpoint_and_reaches_market_api() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_code = f"mock_{uuid4().hex[:12]}"

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    collector = MarketDataCollector(
        provider=MockProvider(code=provider_code),
        application_dependencies=ServiceDependencies(
            unit_of_work=unit_of_work,
            clock=lambda: COLLECTOR_CLOCK,
            id_factory=uuid4,
        ),
        checkpoint_store=SqlAlchemyCollectorCheckpointStore(session_factory),
        run_store=SqlAlchemyCollectorRunStore(session_factory),
        collection_lock=PostgresProviderCollectionLock(engine),
        config=CollectorConfig(page_size=2),
        clock=lambda: COLLECTOR_CLOCK,
    )

    try:
        first = await collector.collect(correlation_id="mock-collector-integration")
        second = await collector.collect()

        assert first.pages == 2
        assert first.markets_created == 3
        assert first.snapshots_created == 3
        assert first.observations_created == 3
        assert second.markets_fetched == 1
        assert second.markets_unchanged == 1
        assert second.snapshots_duplicate == 1
        assert second.observations_duplicate == 1

        async with session_factory() as session:
            checkpoint = await session.get(CollectorCheckpointModel, provider_code)
            persisted_provider = await session.scalar(
                select(ProviderModel).where(ProviderModel.code == provider_code)
            )
            assert persisted_provider is not None
            provider_id = persisted_provider.provider_id
            market_count = await session.scalar(
                select(func.count())
                .select_from(MarketModel)
                .where(MarketModel.provider_id == provider_id)
            )
            snapshot_count = await session.scalar(
                select(func.count())
                .select_from(MarketSnapshotModel)
                .join(
                    MarketModel,
                    MarketModel.market_id == MarketSnapshotModel.market_id,
                )
                .where(MarketModel.provider_id == provider_id)
            )
            observation_count = await session.scalar(
                select(func.count())
                .select_from(MarketObservationModel)
                .join(
                    MarketModel,
                    MarketModel.market_id == MarketObservationModel.market_id,
                )
                .where(MarketModel.provider_id == provider_id)
            )

        assert checkpoint is not None
        assert checkpoint.cursor is None
        assert checkpoint.pending_watermark is None
        assert checkpoint.watermark == datetime(2026, 6, 2, tzinfo=UTC)
        assert market_count == 3
        assert snapshot_count == 3
        assert observation_count == 3

        lock = PostgresProviderCollectionLock(engine)
        async with (
            lock.acquire(provider_code) as first_lock,
            lock.acquire(provider_code) as second_lock,
        ):
            assert first_lock is True
            assert second_lock is False

        application = create_app(settings)
        async with application.router.lifespan_context(application):
            transport = httpx.ASGITransport(app=application)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.get(
                    "/markets",
                    params={"provider": provider_code, "page_size": 10},
                )
                runs_response = await client.get(
                    "/collector-runs",
                    params={"provider": provider_code, "status": "completed"},
                )
                run_detail_response = await client.get(f"/collector-runs/{first.run_id}")

        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert runs_response.status_code == 200
        assert runs_response.json()["total"] == 2
        assert runs_response.json()["items"][0]["status"] == "completed"
        assert run_detail_response.status_code == 200
        assert run_detail_response.json()["run_id"] == str(first.run_id)
        assert run_detail_response.json()["observations_created"] == 3
    finally:
        await _cleanup(session_factory, provider_code)
        await engine.dispose()


async def _cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    provider_code: str,
) -> None:
    async with session_factory.begin() as session:
        provider_id = await session.scalar(
            select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
        )
        if provider_id is not None:
            market_ids = select(MarketModel.market_id).where(MarketModel.provider_id == provider_id)
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
            await session.execute(delete(MarketModel).where(MarketModel.provider_id == provider_id))
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await session.execute(
            delete(CollectorCheckpointModel).where(
                CollectorCheckpointModel.provider_code == provider_code
            )
        )
        await session.execute(
            delete(CollectorRunModel).where(CollectorRunModel.provider_code == provider_code)
        )
