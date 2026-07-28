from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

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
    MarketNotFoundError,
    ObservationConflictError,
    ObservationProviderMismatchError,
    ProviderAlreadyExistsError,
    ProviderDisabledError,
    ProviderNotFoundError,
    SnapshotConflictError,
)
from predictionlab.application.markets.repositories import (
    EntitySync,
    ObservationWrite,
    SnapshotWrite,
)
from predictionlab.application.markets.unit_of_work import MarketUnitOfWorkFactory
from predictionlab.domain.markets import (
    Market,
    MarketObservation,
    MarketSnapshot,
    MarketStateChange,
    MarketStatus,
    Provider,
    ResolutionOutcome,
)
from predictionlab.domain.markets.entities import utc_now

type Clock = Callable[[], datetime]
type IdFactory = Callable[[], UUID]


@dataclass(frozen=True, slots=True)
class ServiceDependencies:
    unit_of_work: MarketUnitOfWorkFactory
    clock: Clock = utc_now
    id_factory: IdFactory = uuid4


class ProviderService:
    def __init__(self, dependencies: ServiceDependencies) -> None:
        self._dependencies = dependencies

    async def create(self, command: CreateProvider) -> Provider:
        now = self._dependencies.clock()
        provider = Provider(
            provider_id=self._dependencies.id_factory(),
            code=command.code,
            name=command.name,
            enabled=command.enabled,
            created_at=now,
            updated_at=now,
        )
        async with self._dependencies.unit_of_work() as unit_of_work:
            if await unit_of_work.providers.get_by_code(provider.code) is not None:
                raise ProviderAlreadyExistsError(f"provider code already exists: {provider.code}")
            await unit_of_work.providers.add(provider)
            await unit_of_work.commit()
        return provider

    async def update(self, command: UpdateProvider) -> Provider:
        async with self._dependencies.unit_of_work() as unit_of_work:
            provider = await unit_of_work.providers.get_by_id(command.provider_id)
            if provider is None:
                raise ProviderNotFoundError(str(command.provider_id))
            updated = provider.update(
                name=command.name,
                enabled=command.enabled,
                changed_at=self._dependencies.clock(),
            )
            if updated != provider and not await unit_of_work.providers.update(updated):
                raise ProviderNotFoundError(str(command.provider_id))
            await unit_of_work.commit()
        return updated

    async def synchronize(
        self,
        command: SynchronizeProvider,
    ) -> EntitySync[Provider]:
        now = self._dependencies.clock()
        async with self._dependencies.unit_of_work() as unit_of_work:
            existing = await unit_of_work.providers.get_by_code(command.code)
            if existing is None:
                provider = Provider(
                    provider_id=self._dependencies.id_factory(),
                    code=command.code,
                    name=command.name,
                    enabled=command.enabled,
                    created_at=now,
                    updated_at=now,
                )
                await unit_of_work.providers.add(provider)
                await unit_of_work.commit()
                return EntitySync(entity=provider, created=True, updated=False)

            synchronized = existing.update(
                name=command.name,
                enabled=command.enabled,
                changed_at=now,
            )
            was_updated = synchronized != existing
            if was_updated and not await unit_of_work.providers.update(synchronized):
                raise ProviderNotFoundError(str(existing.provider_id))
            await unit_of_work.commit()
            return EntitySync(
                entity=synchronized,
                created=False,
                updated=was_updated,
            )


class MarketService:
    def __init__(self, dependencies: ServiceDependencies) -> None:
        self._dependencies = dependencies

    async def create(self, command: CreateMarket) -> Market:
        now = self._dependencies.clock()
        market = Market(
            market_id=self._dependencies.id_factory(),
            provider_id=command.provider_id,
            provider_market_id=command.provider_market_id,
            title=command.title,
            description=command.description,
            category=command.category,
            resolution_at=command.resolution_at,
            source_created_at=command.source_created_at,
            status=command.status,
            resolution_outcome=command.resolution_outcome,
            resolved_at=command.resolved_at,
            resolution_source=command.resolution_source,
            ingested_at=now,
            updated_at=now,
        )
        async with self._dependencies.unit_of_work() as unit_of_work:
            provider = await unit_of_work.providers.get_by_id(command.provider_id)
            if provider is None:
                raise ProviderNotFoundError(str(command.provider_id))
            if not provider.enabled:
                raise ProviderDisabledError(str(command.provider_id))
            existing = await unit_of_work.markets.get_by_provider_reference(
                provider_id=command.provider_id,
                provider_market_id=command.provider_market_id,
            )
            if existing is not None:
                raise MarketAlreadyExistsError(command.provider_market_id)
            await unit_of_work.markets.add(market)
            await unit_of_work.market_history.add(
                _state_change(
                    before=None,
                    after=market,
                    occurred_at=now,
                    change_id=self._dependencies.id_factory(),
                )
            )
            await unit_of_work.commit()
        return market

    async def update(self, command: UpdateMarket) -> Market:
        async with self._dependencies.unit_of_work() as unit_of_work:
            market = await unit_of_work.markets.get_by_id(command.market_id)
            if market is None:
                raise MarketNotFoundError(str(command.market_id))
            updated = market.update_details(
                title=command.title,
                description=command.description,
                category=command.category,
                resolution_at=command.resolution_at,
                source_created_at=command.source_created_at,
                changed_at=self._dependencies.clock(),
            )
            if command.resolution_outcome is ResolutionOutcome.UNRESOLVED:
                updated = _synchronize_market_status(
                    updated,
                    command.status,
                    changed_at=self._dependencies.clock(),
                )
            else:
                updated = _apply_resolution(
                    updated,
                    outcome=command.resolution_outcome,
                    resolved_at=command.resolved_at,
                    source=command.resolution_source,
                    changed_at=self._dependencies.clock(),
                )
            if updated != market and not await unit_of_work.markets.update(updated):
                raise MarketNotFoundError(str(command.market_id))
            if _state_signature(updated) != _state_signature(market):
                await unit_of_work.market_history.add(
                    _state_change(
                        before=market,
                        after=updated,
                        occurred_at=updated.updated_at,
                        change_id=self._dependencies.id_factory(),
                    )
                )
            await unit_of_work.commit()
        return updated

    async def synchronize(
        self,
        command: SynchronizeMarket,
    ) -> EntitySync[Market]:
        now = self._dependencies.clock()
        async with self._dependencies.unit_of_work() as unit_of_work:
            provider = await unit_of_work.providers.get_by_id(command.provider_id)
            if provider is None:
                raise ProviderNotFoundError(str(command.provider_id))
            if not provider.enabled:
                raise ProviderDisabledError(str(command.provider_id))

            existing = await unit_of_work.markets.get_by_provider_reference(
                provider_id=command.provider_id,
                provider_market_id=command.provider_market_id,
            )
            if existing is None:
                market = Market(
                    market_id=self._dependencies.id_factory(),
                    provider_id=command.provider_id,
                    provider_market_id=command.provider_market_id,
                    title=command.title,
                    description=command.description,
                    category=command.category,
                    resolution_at=command.resolution_at,
                    source_created_at=command.source_created_at,
                    status=command.status,
                    resolution_outcome=command.resolution_outcome,
                    resolved_at=command.resolved_at,
                    resolution_source=command.resolution_source,
                    ingested_at=now,
                    updated_at=now,
                )
                await unit_of_work.markets.add(market)
                await unit_of_work.market_history.add(
                    _state_change(
                        before=None,
                        after=market,
                        occurred_at=now,
                        change_id=self._dependencies.id_factory(),
                    )
                )
                await unit_of_work.commit()
                return EntitySync(entity=market, created=True, updated=False)

            synchronized = existing.update_details(
                title=command.title,
                description=command.description,
                category=command.category,
                resolution_at=command.resolution_at,
                source_created_at=command.source_created_at,
                changed_at=now,
            )
            if command.resolution_outcome is ResolutionOutcome.UNRESOLVED:
                synchronized = _synchronize_market_status(
                    synchronized,
                    command.status,
                    changed_at=now,
                )
            else:
                synchronized = _apply_resolution(
                    synchronized,
                    outcome=command.resolution_outcome,
                    resolved_at=command.resolved_at,
                    source=command.resolution_source,
                    changed_at=now,
                )
            was_updated = synchronized != existing
            if was_updated and not await unit_of_work.markets.update(synchronized):
                raise MarketNotFoundError(str(existing.market_id))
            if _state_signature(synchronized) != _state_signature(existing):
                await unit_of_work.market_history.add(
                    _state_change(
                        before=existing,
                        after=synchronized,
                        occurred_at=synchronized.updated_at,
                        change_id=self._dependencies.id_factory(),
                    )
                )
            await unit_of_work.commit()
            return EntitySync(
                entity=synchronized,
                created=False,
                updated=was_updated,
            )


class MarketSnapshotService:
    def __init__(self, dependencies: ServiceDependencies) -> None:
        self._dependencies = dependencies

    async def record(self, command: RecordMarketSnapshot) -> SnapshotWrite:
        snapshot = MarketSnapshot(
            snapshot_id=self._dependencies.id_factory(),
            market_id=command.market_id,
            observed_at=command.observed_at,
            yes_price=command.yes_price,
            no_price=command.no_price,
            probability=command.probability,
            spread=command.spread,
            volume=command.volume,
            liquidity=command.liquidity,
        )
        async with self._dependencies.unit_of_work() as unit_of_work:
            market = await unit_of_work.markets.get_by_id(command.market_id)
            if market is None:
                raise MarketNotFoundError(str(command.market_id))
            market.validate_snapshot(snapshot)
            result = await unit_of_work.snapshots.add_if_absent(snapshot)
            if not result.created and not _same_observation(snapshot, result.snapshot):
                raise SnapshotConflictError("an observation already exists with different values")
            await unit_of_work.commit()
        return result


class MarketObservationService:
    def __init__(self, dependencies: ServiceDependencies) -> None:
        self._dependencies = dependencies

    async def record(
        self,
        command: RecordMarketObservation,
    ) -> ObservationWrite:
        observation = MarketObservation(
            observation_id=self._dependencies.id_factory(),
            market_id=command.market_id,
            observed_at=command.observed_at,
            provider_code=command.provider_code,
            probability=command.probability,
            volume=command.volume,
            liquidity=command.liquidity,
            source_updated_at=command.source_updated_at,
            ingested_at=self._dependencies.clock(),
            raw_payload_hash=command.raw_payload_hash,
        )
        async with self._dependencies.unit_of_work() as unit_of_work:
            market = await unit_of_work.markets.get_by_id(command.market_id)
            if market is None:
                raise MarketNotFoundError(str(command.market_id))
            provider = await unit_of_work.providers.get_by_id(market.provider_id)
            if provider is None:
                raise ProviderNotFoundError(str(market.provider_id))
            if provider.code != observation.provider_code:
                raise ObservationProviderMismatchError(
                    "observation provider does not own the market"
                )
            market.validate_observation(observation)
            result = await unit_of_work.observations.add_if_absent(observation)
            if not result.created and not _same_market_observation(
                observation,
                result.observation,
            ):
                raise ObservationConflictError(
                    "an observation already exists with different values"
                )
            await unit_of_work.commit()
        return result


def _same_observation(left: MarketSnapshot, right: MarketSnapshot) -> bool:
    return (
        left.market_id == right.market_id
        and left.observed_at == right.observed_at
        and left.yes_price == right.yes_price
        and left.no_price == right.no_price
        and left.probability == right.probability
        and left.spread == right.spread
        and left.volume == right.volume
        and left.liquidity == right.liquidity
    )


def _same_market_observation(
    left: MarketObservation,
    right: MarketObservation,
) -> bool:
    return (
        left.market_id == right.market_id
        and left.observed_at == right.observed_at
        and left.provider_code == right.provider_code
        and left.probability == right.probability
        and left.volume == right.volume
        and left.liquidity == right.liquidity
        and left.source_updated_at == right.source_updated_at
        and left.raw_payload_hash == right.raw_payload_hash
    )


def _synchronize_market_status(
    market: Market,
    status: MarketStatus,
    *,
    changed_at: datetime,
) -> Market:
    if market.status is MarketStatus.OPEN and status is MarketStatus.RESOLVED:
        market = market.transition_to(
            MarketStatus.CLOSED,
            changed_at=changed_at,
        )
    return market.transition_to(status, changed_at=changed_at)


def _apply_resolution(
    market: Market,
    *,
    outcome: ResolutionOutcome,
    resolved_at: datetime | None,
    source: str | None,
    changed_at: datetime,
) -> Market:
    if outcome is ResolutionOutcome.UNRESOLVED:
        return market
    return market.apply_resolution(
        outcome=outcome,
        resolved_at=resolved_at,
        source=source,
        changed_at=changed_at,
    )


def _state_signature(
    market: Market,
) -> tuple[MarketStatus, ResolutionOutcome, datetime | None, str | None]:
    return (
        market.status,
        market.resolution_outcome,
        market.resolved_at,
        market.resolution_source,
    )


def _state_change(
    *,
    before: Market | None,
    after: Market,
    occurred_at: datetime,
    change_id: UUID,
) -> MarketStateChange:
    return MarketStateChange(
        change_id=change_id,
        market_id=after.market_id,
        occurred_at=occurred_at,
        previous_status=before.status if before is not None else None,
        status=after.status,
        previous_resolution_outcome=(before.resolution_outcome if before is not None else None),
        resolution_outcome=after.resolution_outcome,
        resolved_at=after.resolved_at,
        resolution_source=after.resolution_source,
    )
