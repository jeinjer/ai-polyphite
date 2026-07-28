from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from predictionlab.application.markets.commands import (
    CreateMarket,
    CreateProvider,
    RecordMarketObservation,
    RecordMarketSnapshot,
    SynchronizeMarket,
    SynchronizeProvider,
    UpdateMarket,
    UpdateProvider,
)
from predictionlab.application.markets.errors import (
    MarketAlreadyExistsError,
    ObservationConflictError,
    ObservationProviderMismatchError,
    ProviderAlreadyExistsError,
    ProviderDisabledError,
    SnapshotConflictError,
)
from predictionlab.application.markets.repositories import (
    ObservationWrite,
    SnapshotWrite,
)
from predictionlab.application.markets.services import (
    MarketObservationService,
    MarketService,
    MarketSnapshotService,
    ProviderService,
    ServiceDependencies,
)
from predictionlab.domain.markets import (
    Market,
    MarketObservation,
    MarketSnapshot,
    MarketStateChange,
    MarketStatus,
    Provider,
    ResolutionOutcome,
)

NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


class FakeProviderRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Provider] = {}

    async def add(self, provider: Provider) -> None:
        self.items[provider.provider_id] = provider

    async def update(self, provider: Provider) -> bool:
        if provider.provider_id not in self.items:
            return False
        self.items[provider.provider_id] = provider
        return True

    async def get_by_id(self, provider_id: UUID) -> Provider | None:
        return self.items.get(provider_id)

    async def get_by_code(self, code: str) -> Provider | None:
        return next((item for item in self.items.values() if item.code == code), None)


class FakeMarketRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Market] = {}

    async def add(self, market: Market) -> None:
        self.items[market.market_id] = market

    async def update(self, market: Market) -> bool:
        if market.market_id not in self.items:
            return False
        self.items[market.market_id] = market
        return True

    async def get_by_id(self, market_id: UUID) -> Market | None:
        return self.items.get(market_id)

    async def get_by_provider_reference(
        self,
        *,
        provider_id: UUID,
        provider_market_id: str,
    ) -> Market | None:
        return next(
            (
                item
                for item in self.items.values()
                if item.provider_id == provider_id and item.provider_market_id == provider_market_id
            ),
            None,
        )


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[UUID, datetime], MarketSnapshot] = {}

    async def add(self, snapshot: MarketSnapshot) -> None:
        self.items[(snapshot.market_id, snapshot.observed_at)] = snapshot

    async def add_if_absent(self, snapshot: MarketSnapshot) -> SnapshotWrite:
        key = (snapshot.market_id, snapshot.observed_at)
        existing = self.items.get(key)
        if existing is not None:
            return SnapshotWrite(snapshot=existing, created=False)
        self.items[key] = snapshot
        return SnapshotWrite(snapshot=snapshot, created=True)

    async def get_by_id(self, snapshot_id: UUID) -> MarketSnapshot | None:
        return next(
            (item for item in self.items.values() if item.snapshot_id == snapshot_id),
            None,
        )

    async def latest_for_market(self, market_id: UUID) -> MarketSnapshot | None:
        snapshots = [item for item in self.items.values() if item.market_id == market_id]
        return max(snapshots, key=lambda item: item.observed_at, default=None)

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> tuple[MarketSnapshot, ...]:
        snapshots = sorted(
            (item for item in self.items.values() if item.market_id == market_id),
            key=lambda item: item.observed_at,
            reverse=True,
        )
        return tuple(snapshots[:limit])


class FakeObservationRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[UUID, datetime], MarketObservation] = {}

    async def add_if_absent(
        self,
        observation: MarketObservation,
    ) -> ObservationWrite:
        key = (observation.market_id, observation.observed_at)
        existing = self.items.get(key)
        if existing is not None:
            return ObservationWrite(observation=existing, created=False)
        self.items[key] = observation
        return ObservationWrite(observation=observation, created=True)

    async def latest_for_market(
        self,
        market_id: UUID,
    ) -> MarketObservation | None:
        observations = [item for item in self.items.values() if item.market_id == market_id]
        return max(observations, key=lambda item: item.observed_at, default=None)

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> tuple[MarketObservation, ...]:
        observations = sorted(
            (item for item in self.items.values() if item.market_id == market_id),
            key=lambda item: item.observed_at,
            reverse=True,
        )
        return tuple(observations[:limit])


class FakeMarketHistoryRepository:
    def __init__(self) -> None:
        self.items: list[MarketStateChange] = []

    async def add(self, change: MarketStateChange) -> None:
        self.items.append(change)


class FakeUnitOfWork:
    def __init__(
        self,
        providers: FakeProviderRepository,
        markets: FakeMarketRepository,
        snapshots: FakeSnapshotRepository,
        observations: FakeObservationRepository,
        market_history: FakeMarketHistoryRepository,
    ) -> None:
        self.providers = providers
        self.markets = markets
        self.snapshots = snapshots
        self.observations = observations
        self.market_history = market_history
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if exc_type is not None or not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeUnitOfWorkFactory:
    def __init__(self) -> None:
        self.providers = FakeProviderRepository()
        self.markets = FakeMarketRepository()
        self.snapshots = FakeSnapshotRepository()
        self.observations = FakeObservationRepository()
        self.market_history = FakeMarketHistoryRepository()
        self.created: list[FakeUnitOfWork] = []

    def __call__(self) -> FakeUnitOfWork:
        unit_of_work = FakeUnitOfWork(
            self.providers,
            self.markets,
            self.snapshots,
            self.observations,
            self.market_history,
        )
        self.created.append(unit_of_work)
        return unit_of_work


class IdFactory:
    def __init__(self, *identifiers: UUID) -> None:
        self._identifiers = iter(identifiers)

    def __call__(self) -> UUID:
        return next(self._identifiers, uuid4())


def dependencies(
    factory: FakeUnitOfWorkFactory,
    *identifiers: UUID,
) -> ServiceDependencies:
    return ServiceDependencies(
        unit_of_work=factory,
        clock=lambda: NOW,
        id_factory=IdFactory(*identifiers),
    )


def snapshot_command(market_id: UUID, **overrides: object) -> RecordMarketSnapshot:
    values: dict[str, object] = {
        "market_id": market_id,
        "observed_at": NOW + timedelta(minutes=1),
        "yes_price": Decimal("0.60"),
        "no_price": Decimal("0.42"),
        "probability": Decimal("0.59"),
        "spread": Decimal("0.02"),
        "volume": Decimal("100"),
        "liquidity": Decimal("50"),
    }
    values.update(overrides)
    return RecordMarketSnapshot(**values)  # type: ignore[arg-type]


def observation_command(
    market_id: UUID,
    **overrides: object,
) -> RecordMarketObservation:
    values: dict[str, object] = {
        "market_id": market_id,
        "observed_at": NOW + timedelta(minutes=1),
        "provider_code": "provider",
        "probability": Decimal("0.59"),
        "volume": None,
        "liquidity": Decimal("50"),
        "source_updated_at": NOW,
        "raw_payload_hash": "a" * 64,
    }
    values.update(overrides)
    return RecordMarketObservation(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_provider_service_creates_updates_and_commits() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    create_service = ProviderService(dependencies(factory, provider_id))

    provider = await create_service.create(CreateProvider(code="provider", name="Provider"))
    updated = await ProviderService(dependencies(factory, uuid4())).update(
        UpdateProvider(
            provider_id=provider_id,
            name="Updated Provider",
            enabled=False,
        )
    )

    assert provider.provider_id == provider_id
    assert updated.enabled is False
    assert factory.providers.items[provider_id] == updated
    assert all(unit.committed for unit in factory.created)


@pytest.mark.asyncio
async def test_provider_service_rejects_duplicate_code() -> None:
    factory = FakeUnitOfWorkFactory()
    service = ProviderService(dependencies(factory, uuid4(), uuid4()))
    await service.create(CreateProvider(code="provider", name="Provider"))

    with pytest.raises(ProviderAlreadyExistsError):
        await service.create(CreateProvider(code="provider", name="Duplicate"))

    assert factory.created[-1].rolled_back is True


@pytest.mark.asyncio
async def test_provider_service_synchronizes_idempotently() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    service = ProviderService(dependencies(factory, provider_id))

    created = await service.synchronize(SynchronizeProvider(code="provider", name="Provider"))
    updated = await service.synchronize(
        SynchronizeProvider(code="provider", name="Updated Provider")
    )
    unchanged = await service.synchronize(
        SynchronizeProvider(code="provider", name="Updated Provider")
    )

    assert created.created is True
    assert created.updated is False
    assert updated.created is False
    assert updated.updated is True
    assert unchanged.created is False
    assert unchanged.updated is False
    assert unchanged.entity.provider_id == provider_id


@pytest.mark.asyncio
async def test_market_service_requires_an_enabled_provider() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="disabled",
        name="Disabled",
        enabled=False,
        created_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(ProviderDisabledError):
        await MarketService(dependencies(factory, uuid4())).create(
            CreateMarket(
                provider_id=provider_id,
                provider_market_id="external-1",
                title="Market",
                status=MarketStatus.OPEN,
            )
        )


@pytest.mark.asyncio
async def test_market_service_creates_and_updates_market() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    market_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    service = MarketService(dependencies(factory, market_id))
    created = await service.create(
        CreateMarket(
            provider_id=provider_id,
            provider_market_id="external-1",
            title="Market",
            status=MarketStatus.OPEN,
        )
    )
    updated = await MarketService(dependencies(factory, uuid4())).update(
        UpdateMarket(
            market_id=market_id,
            title="Updated market",
            description="Description",
            category="science",
            resolution_at=NOW + timedelta(days=1),
            source_created_at=None,
            status=MarketStatus.CLOSED,
        )
    )

    assert created.status is MarketStatus.OPEN
    assert updated.status is MarketStatus.CLOSED
    assert updated.title == "Updated market"
    assert factory.markets.items[market_id] == updated


@pytest.mark.asyncio
async def test_market_service_rejects_duplicate_provider_reference() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    service = MarketService(dependencies(factory, uuid4(), uuid4()))
    command = CreateMarket(
        provider_id=provider_id,
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
    )
    await service.create(command)

    with pytest.raises(MarketAlreadyExistsError):
        await service.create(command)


@pytest.mark.asyncio
async def test_market_service_synchronizes_by_external_reference() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    market_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    service = MarketService(dependencies(factory, market_id))

    created = await service.synchronize(
        SynchronizeMarket(
            provider_id=provider_id,
            provider_market_id="external-1",
            title="Market",
            status=MarketStatus.OPEN,
        )
    )
    updated = await service.synchronize(
        SynchronizeMarket(
            provider_id=provider_id,
            provider_market_id="external-1",
            title="Resolved market",
            status=MarketStatus.RESOLVED,
        )
    )
    unchanged = await service.synchronize(
        SynchronizeMarket(
            provider_id=provider_id,
            provider_market_id="external-1",
            title="Resolved market",
            status=MarketStatus.RESOLVED,
        )
    )

    assert created.created is True
    assert updated.updated is True
    assert updated.entity.status is MarketStatus.RESOLVED
    assert unchanged.updated is False
    assert len(factory.markets.items) == 1


@pytest.mark.asyncio
async def test_market_sync_enriches_legacy_ambiguous_resolution() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    market_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=provider_id,
        provider_market_id="legacy-resolved",
        title="Legacy market",
        status=MarketStatus.RESOLVED,
        ingested_at=NOW,
        updated_at=NOW,
    )

    result = await MarketService(dependencies(factory, uuid4())).synchronize(
        SynchronizeMarket(
            provider_id=provider_id,
            provider_market_id="legacy-resolved",
            title="Legacy market",
            status=MarketStatus.RESOLVED,
            resolution_outcome=ResolutionOutcome.YES,
            resolved_at=NOW + timedelta(hours=1),
            resolution_source="provider_public_api",
        )
    )

    assert result.updated is True
    assert result.entity.resolution_outcome is ResolutionOutcome.YES


@pytest.mark.asyncio
async def test_snapshot_service_is_idempotent() -> None:
    factory = FakeUnitOfWorkFactory()
    market_id = uuid4()
    first_snapshot_id = uuid4()
    second_snapshot_id = uuid4()
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=uuid4(),
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )
    service = MarketSnapshotService(dependencies(factory, first_snapshot_id, second_snapshot_id))
    command = snapshot_command(market_id)

    first = await service.record(command)
    repeated = await service.record(command)

    assert first.created is True
    assert repeated.created is False
    assert repeated.snapshot.snapshot_id == first_snapshot_id
    assert len(factory.snapshots.items) == 1


@pytest.mark.asyncio
async def test_snapshot_service_rejects_conflicting_observation() -> None:
    factory = FakeUnitOfWorkFactory()
    market_id = uuid4()
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=uuid4(),
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )
    service = MarketSnapshotService(dependencies(factory, uuid4(), uuid4()))
    await service.record(snapshot_command(market_id))

    with pytest.raises(SnapshotConflictError):
        await service.record(snapshot_command(market_id, yes_price=Decimal("0.61")))

    assert factory.created[-1].rolled_back is True


@pytest.mark.asyncio
async def test_observation_service_is_idempotent_and_preserves_nulls() -> None:
    factory = FakeUnitOfWorkFactory()
    market_id = uuid4()
    observation_id = uuid4()
    provider_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=provider_id,
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )
    service = MarketObservationService(dependencies(factory, observation_id, uuid4()))
    command = observation_command(market_id)

    first = await service.record(command)
    repeated = await service.record(command)

    assert first.created is True
    assert repeated.created is False
    assert repeated.observation.observation_id == observation_id
    assert repeated.observation.volume is None
    assert len(factory.observations.items) == 1


@pytest.mark.asyncio
async def test_observation_service_rejects_conflicting_values() -> None:
    factory = FakeUnitOfWorkFactory()
    market_id = uuid4()
    provider_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=provider_id,
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )
    service = MarketObservationService(dependencies(factory, uuid4(), uuid4()))
    await service.record(observation_command(market_id))

    with pytest.raises(ObservationConflictError):
        await service.record(observation_command(market_id, probability=Decimal("0.61")))


@pytest.mark.asyncio
async def test_observation_service_rejects_wrong_provenance() -> None:
    factory = FakeUnitOfWorkFactory()
    provider_id = uuid4()
    market_id = uuid4()
    factory.providers.items[provider_id] = Provider(
        provider_id=provider_id,
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    factory.markets.items[market_id] = Market(
        market_id=market_id,
        provider_id=provider_id,
        provider_market_id="external-1",
        title="Market",
        status=MarketStatus.OPEN,
        ingested_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(ObservationProviderMismatchError):
        await MarketObservationService(dependencies(factory, uuid4())).record(
            observation_command(
                market_id,
                provider_code="another_provider",
            )
        )
