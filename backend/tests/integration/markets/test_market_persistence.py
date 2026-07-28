from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from predictionlab.domain.markets import (
    Market,
    MarketObservation,
    MarketSnapshot,
    MarketStatus,
    Provider,
)
from predictionlab.infrastructure.database.models import MarketSnapshotModel
from predictionlab.infrastructure.database.repositories import (
    SqlAlchemyMarketObservationRepository,
    SqlAlchemyMarketRepository,
    SqlAlchemyMarketSnapshotRepository,
    SqlAlchemyProviderRepository,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def provider(*, code: str = "test_provider") -> Provider:
    return Provider(
        code=code,
        name="Test Provider",
        created_at=NOW,
        updated_at=NOW,
    )


def market(provider_id, *, provider_market_id: str = "external-1") -> Market:
    return Market(
        provider_id=provider_id,
        provider_market_id=provider_market_id,
        title="Will the persistence test pass?",
        description="Persistence integration fixture.",
        category="engineering",
        resolution_at=NOW + timedelta(days=1),
        source_created_at=NOW - timedelta(days=2),
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )


def snapshot(
    market_id,
    *,
    observed_at: datetime = NOW,
    yes_price: Decimal = Decimal("0.61"),
) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        observed_at=observed_at,
        yes_price=yes_price,
        no_price=Decimal("0.42"),
        probability=Decimal("0.60"),
        spread=Decimal("0.03"),
        volume=Decimal("1000.12345678"),
        liquidity=Decimal("500.87654321"),
    )


def observation(
    market_id,
    *,
    observed_at: datetime = NOW,
    probability: Decimal | None = Decimal("0.60"),
) -> MarketObservation:
    return MarketObservation(
        market_id=market_id,
        observed_at=observed_at,
        provider_code="test_provider",
        ingested_at=NOW + timedelta(minutes=2),
        probability=probability,
        volume=Decimal("1000.12345678"),
        liquidity=None,
        source_updated_at=NOW - timedelta(minutes=1),
        raw_payload_hash="a" * 64,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_created_market_schema(db_session: AsyncSession) -> None:
    connection = await db_session.connection()
    tables = await connection.run_sync(
        lambda sync_connection: set(inspect(sync_connection).get_table_names())
    )

    assert {
        "alembic_version",
        "providers",
        "markets",
        "market_snapshots",
        "market_observations",
        "market_state_history",
        "collector_runs",
    } <= tables


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repositories_round_trip_market_graph(
    db_session: AsyncSession,
) -> None:
    provider_repository = SqlAlchemyProviderRepository(db_session)
    market_repository = SqlAlchemyMarketRepository(db_session)
    snapshot_repository = SqlAlchemyMarketSnapshotRepository(db_session)
    saved_provider = provider()
    saved_market = market(saved_provider.provider_id)
    older_snapshot = snapshot(saved_market.market_id)
    newer_snapshot = snapshot(
        saved_market.market_id,
        observed_at=NOW + timedelta(minutes=1),
        yes_price=Decimal("0.64"),
    )

    await provider_repository.add(saved_provider)
    await market_repository.add(saved_market)
    await snapshot_repository.add(older_snapshot)
    await snapshot_repository.add(newer_snapshot)

    loaded_provider = await provider_repository.get_by_code(saved_provider.code)
    loaded_market = await market_repository.get_by_provider_reference(
        provider_id=saved_provider.provider_id,
        provider_market_id=saved_market.provider_market_id,
    )
    loaded_snapshots = await snapshot_repository.list_for_market(
        saved_market.market_id,
        limit=10,
    )
    latest = await snapshot_repository.latest_for_market(saved_market.market_id)

    assert loaded_provider == saved_provider
    assert loaded_market == saved_market
    assert loaded_snapshots == (newer_snapshot, older_snapshot)
    assert latest == newer_snapshot
    assert latest.yes_price == Decimal("0.64")
    assert latest.volume == Decimal("1000.12345678")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_code_is_unique(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProviderRepository(db_session)

    await repository.add(provider())

    with pytest.raises(IntegrityError):
        await repository.add(provider())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_provider_reference_is_unique(
    db_session: AsyncSession,
) -> None:
    provider_repository = SqlAlchemyProviderRepository(db_session)
    market_repository = SqlAlchemyMarketRepository(db_session)
    saved_provider = provider()
    await provider_repository.add(saved_provider)
    await market_repository.add(market(saved_provider.provider_id))

    with pytest.raises(IntegrityError):
        await market_repository.add(market(saved_provider.provider_id))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_observation_is_idempotent_per_market(
    db_session: AsyncSession,
) -> None:
    provider_repository = SqlAlchemyProviderRepository(db_session)
    market_repository = SqlAlchemyMarketRepository(db_session)
    snapshot_repository = SqlAlchemyMarketSnapshotRepository(db_session)
    saved_provider = provider()
    saved_market = market(saved_provider.provider_id)
    await provider_repository.add(saved_provider)
    await market_repository.add(saved_market)
    await snapshot_repository.add(snapshot(saved_market.market_id))

    with pytest.raises(IntegrityError):
        await snapshot_repository.add(snapshot(saved_market.market_id))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_rejects_invalid_snapshot_price(
    db_session: AsyncSession,
) -> None:
    provider_repository = SqlAlchemyProviderRepository(db_session)
    market_repository = SqlAlchemyMarketRepository(db_session)
    saved_provider = provider()
    saved_market = market(saved_provider.provider_id)
    await provider_repository.add(saved_provider)
    await market_repository.add(saved_market)
    db_session.add(
        MarketSnapshotModel(
            snapshot_id=uuid4(),
            market_id=saved_market.market_id,
            observed_at=NOW,
            yes_price=Decimal("1.1"),
            no_price=Decimal("0"),
            probability=Decimal("1"),
            spread=Decimal("0"),
            volume=Decimal("0"),
            liquidity=Decimal("0"),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_repository_requires_positive_limit(
    db_session: AsyncSession,
) -> None:
    repository = SqlAlchemyMarketSnapshotRepository(db_session)

    with pytest.raises(ValueError, match="limit must be positive"):
        await repository.list_for_market(uuid4(), limit=0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_observation_repository_is_idempotent_and_round_trips_nulls(
    db_session: AsyncSession,
) -> None:
    provider_repository = SqlAlchemyProviderRepository(db_session)
    market_repository = SqlAlchemyMarketRepository(db_session)
    observation_repository = SqlAlchemyMarketObservationRepository(db_session)
    saved_provider = provider()
    saved_market = market(saved_provider.provider_id)
    saved_observation = observation(saved_market.market_id)
    await provider_repository.add(saved_provider)
    await market_repository.add(saved_market)

    first = await observation_repository.add_if_absent(saved_observation)
    repeated = await observation_repository.add_if_absent(saved_observation)
    latest = await observation_repository.latest_for_market(saved_market.market_id)

    assert first.created is True
    assert repeated.created is False
    assert latest == saved_observation
    assert latest is not None
    assert latest.liquidity is None
