from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.application.markets.commands import (
    CreateMarket,
    CreateProvider,
    RecordMarketSnapshot,
    UpdateMarket,
    UpdateProvider,
)
from predictionlab.application.markets.errors import SnapshotConflictError
from predictionlab.application.markets.services import (
    MarketService,
    MarketSnapshotService,
    ProviderService,
    ServiceDependencies,
)
from predictionlab.core.settings import Settings
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

NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


def snapshot_command(
    market_id: UUID,
    *,
    yes_price: Decimal = Decimal("0.60"),
) -> RecordMarketSnapshot:
    return RecordMarketSnapshot(
        market_id=market_id,
        observed_at=NOW + timedelta(minutes=1),
        yes_price=yes_price,
        no_price=Decimal("0.42"),
        probability=Decimal("0.59"),
        spread=Decimal("0.02"),
        volume=Decimal("100.12345678"),
        liquidity=Decimal("50.87654321"),
    )


def create_context():
    engine = create_async_engine(str(Settings(_env_file=None).database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    dependencies = ServiceDependencies(
        unit_of_work=unit_of_work,
        clock=lambda: NOW,
        id_factory=uuid4,
    )
    return engine, session_factory, unit_of_work, dependencies


async def cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    provider_id: UUID,
    market_id: UUID,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(MarketSnapshotModel).where(MarketSnapshotModel.market_id == market_id)
        )
        await session.execute(
            delete(MarketObservationModel).where(MarketObservationModel.market_id == market_id)
        )
        await session.execute(
            delete(MarketStateChangeModel).where(MarketStateChangeModel.market_id == market_id)
        )
        await session.execute(delete(MarketModel).where(MarketModel.market_id == market_id))
        await session.execute(delete(ProviderModel).where(ProviderModel.provider_id == provider_id))
        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_application_services_commit_complete_market_flow() -> None:
    engine, session_factory, unit_of_work, dependencies = create_context()
    provider_id: UUID | None = None
    market_id: UUID | None = None

    try:
        provider = await ProviderService(dependencies).create(
            CreateProvider(
                code=f"provider_{uuid4().hex}",
                name="Provider",
            )
        )
        provider_id = provider.provider_id
        market = await MarketService(dependencies).create(
            CreateMarket(
                provider_id=provider.provider_id,
                provider_market_id="external-1",
                title="Market",
                status=MarketStatus.OPEN,
            )
        )
        market_id = market.market_id
        updated_provider = await ProviderService(dependencies).update(
            UpdateProvider(
                provider_id=provider.provider_id,
                name="Updated Provider",
                enabled=True,
            )
        )
        updated_market = await MarketService(dependencies).update(
            UpdateMarket(
                market_id=market.market_id,
                title="Updated Market",
                description="Description",
                category="engineering",
                resolution_at=NOW + timedelta(days=1),
                source_created_at=None,
                status=MarketStatus.CLOSED,
            )
        )
        first = await MarketSnapshotService(dependencies).record(snapshot_command(market.market_id))
        repeated = await MarketSnapshotService(dependencies).record(
            snapshot_command(market.market_id)
        )

        with pytest.raises(SnapshotConflictError):
            await MarketSnapshotService(dependencies).record(
                snapshot_command(
                    market.market_id,
                    yes_price=Decimal("0.61"),
                )
            )

        async with unit_of_work() as reader:
            stored_provider = await reader.providers.get_by_id(provider.provider_id)
            stored_market = await reader.markets.get_by_id(market.market_id)
            stored_snapshots = await reader.snapshots.list_for_market(
                market.market_id,
                limit=10,
            )

        assert stored_provider == updated_provider
        assert stored_market == updated_market
        assert first.created is True
        assert repeated.created is False
        assert repeated.snapshot.snapshot_id == first.snapshot.snapshot_id
        assert stored_snapshots == (first.snapshot,)
    finally:
        if provider_id is not None and market_id is not None:
            await cleanup(
                session_factory,
                provider_id=provider_id,
                market_id=market_id,
            )
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_snapshot_writes_are_idempotent() -> None:
    engine, session_factory, _, dependencies = create_context()
    provider_id: UUID | None = None
    market_id: UUID | None = None

    try:
        provider = await ProviderService(dependencies).create(
            CreateProvider(
                code=f"provider_{uuid4().hex}",
                name="Provider",
            )
        )
        provider_id = provider.provider_id
        market = await MarketService(dependencies).create(
            CreateMarket(
                provider_id=provider.provider_id,
                provider_market_id="external-concurrent",
                title="Concurrent market",
                status=MarketStatus.OPEN,
            )
        )
        market_id = market.market_id
        service = MarketSnapshotService(dependencies)
        command = snapshot_command(market.market_id)

        results = await asyncio.gather(
            service.record(command),
            service.record(command),
        )

        async with session_factory() as session:
            snapshot_count = await session.scalar(
                select(func.count())
                .select_from(MarketSnapshotModel)
                .where(MarketSnapshotModel.market_id == market.market_id)
            )

        assert sum(result.created for result in results) == 1
        assert results[0].snapshot.snapshot_id == results[1].snapshot.snapshot_id
        assert snapshot_count == 1
    finally:
        if provider_id is not None and market_id is not None:
            await cleanup(
                session_factory,
                provider_id=provider_id,
                market_id=market_id,
            )
        await engine.dispose()
