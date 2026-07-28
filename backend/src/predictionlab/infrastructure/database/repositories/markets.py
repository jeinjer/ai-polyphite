from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from predictionlab.application.markets.repositories import (
    ObservationWrite,
    SnapshotWrite,
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
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)


class SqlAlchemyProviderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, provider: Provider) -> None:
        self._session.add(_provider_model(provider))
        await self._session.flush()

    async def update(self, provider: Provider) -> bool:
        provider_id = await self._session.scalar(
            update(ProviderModel)
            .where(ProviderModel.provider_id == provider.provider_id)
            .values(
                name=provider.name,
                enabled=provider.enabled,
                updated_at=provider.updated_at,
            )
            .returning(ProviderModel.provider_id)
        )
        return provider_id is not None

    async def get_by_id(self, provider_id: UUID) -> Provider | None:
        model = await self._session.get(ProviderModel, provider_id)
        return _provider_entity(model) if model is not None else None

    async def get_by_code(self, code: str) -> Provider | None:
        model = await self._session.scalar(select(ProviderModel).where(ProviderModel.code == code))
        return _provider_entity(model) if model is not None else None


class SqlAlchemyMarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, market: Market) -> None:
        self._session.add(_market_model(market))
        await self._session.flush()

    async def update(self, market: Market) -> bool:
        market_id = await self._session.scalar(
            update(MarketModel)
            .where(MarketModel.market_id == market.market_id)
            .values(
                title=market.title,
                description=market.description,
                category=market.category,
                resolution_at=market.resolution_at,
                source_created_at=market.source_created_at,
                status=market.status.value,
                resolution_outcome=market.resolution_outcome.value,
                resolved_at=market.resolved_at,
                resolution_source=market.resolution_source,
                updated_at=market.updated_at,
            )
            .returning(MarketModel.market_id)
        )
        return market_id is not None

    async def get_by_id(self, market_id: UUID) -> Market | None:
        model = await self._session.get(MarketModel, market_id)
        return _market_entity(model) if model is not None else None

    async def get_by_provider_reference(
        self,
        *,
        provider_id: UUID,
        provider_market_id: str,
    ) -> Market | None:
        model = await self._session.scalar(
            select(MarketModel).where(
                MarketModel.provider_id == provider_id,
                MarketModel.provider_market_id == provider_market_id,
            )
        )
        return _market_entity(model) if model is not None else None


class SqlAlchemyMarketSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: MarketSnapshot) -> None:
        self._session.add(_snapshot_model(snapshot))
        await self._session.flush()

    async def add_if_absent(self, snapshot: MarketSnapshot) -> SnapshotWrite:
        inserted_id = await self._session.scalar(
            insert(MarketSnapshotModel)
            .values(**_snapshot_values(snapshot))
            .on_conflict_do_nothing(constraint="uq_market_snapshots_market_observed_at")
            .returning(MarketSnapshotModel.snapshot_id)
        )
        if inserted_id is not None:
            return SnapshotWrite(snapshot=snapshot, created=True)

        existing = await self._session.scalar(
            select(MarketSnapshotModel).where(
                MarketSnapshotModel.market_id == snapshot.market_id,
                MarketSnapshotModel.observed_at == snapshot.observed_at,
            )
        )
        if existing is None:
            raise RuntimeError("conflicting snapshot disappeared before it was read")
        return SnapshotWrite(snapshot=_snapshot_entity(existing), created=False)

    async def get_by_id(self, snapshot_id: UUID) -> MarketSnapshot | None:
        model = await self._session.get(MarketSnapshotModel, snapshot_id)
        return _snapshot_entity(model) if model is not None else None

    async def latest_for_market(self, market_id: UUID) -> MarketSnapshot | None:
        model = await self._session.scalar(
            select(MarketSnapshotModel)
            .where(MarketSnapshotModel.market_id == market_id)
            .order_by(MarketSnapshotModel.observed_at.desc())
            .limit(1)
        )
        return _snapshot_entity(model) if model is not None else None

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> Sequence[MarketSnapshot]:
        if limit < 1:
            raise ValueError("limit must be positive")
        models = (
            await self._session.scalars(
                select(MarketSnapshotModel)
                .where(MarketSnapshotModel.market_id == market_id)
                .order_by(MarketSnapshotModel.observed_at.desc())
                .limit(limit)
            )
        ).all()
        return tuple(_snapshot_entity(model) for model in models)


class SqlAlchemyMarketObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(
        self,
        observation: MarketObservation,
    ) -> ObservationWrite:
        inserted_id = await self._session.scalar(
            insert(MarketObservationModel)
            .values(**_observation_values(observation))
            .on_conflict_do_nothing(constraint="uq_market_observations_market_observed_at")
            .returning(MarketObservationModel.observation_id)
        )
        if inserted_id is not None:
            return ObservationWrite(observation=observation, created=True)
        existing = await self._session.scalar(
            select(MarketObservationModel).where(
                MarketObservationModel.market_id == observation.market_id,
                MarketObservationModel.observed_at == observation.observed_at,
            )
        )
        if existing is None:
            raise RuntimeError("conflicting observation disappeared before it was read")
        return ObservationWrite(
            observation=_observation_entity(existing),
            created=False,
        )

    async def latest_for_market(
        self,
        market_id: UUID,
    ) -> MarketObservation | None:
        model = await self._session.scalar(
            select(MarketObservationModel)
            .where(MarketObservationModel.market_id == market_id)
            .order_by(
                MarketObservationModel.observed_at.desc(),
                MarketObservationModel.observation_id.desc(),
            )
            .limit(1)
        )
        return _observation_entity(model) if model is not None else None

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> Sequence[MarketObservation]:
        if limit < 1:
            raise ValueError("limit must be positive")
        models = (
            await self._session.scalars(
                select(MarketObservationModel)
                .where(MarketObservationModel.market_id == market_id)
                .order_by(
                    MarketObservationModel.observed_at.desc(),
                    MarketObservationModel.observation_id.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(_observation_entity(model) for model in models)


class SqlAlchemyMarketStateHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, change: MarketStateChange) -> None:
        self._session.add(
            MarketStateChangeModel(
                change_id=change.change_id,
                market_id=change.market_id,
                occurred_at=change.occurred_at,
                previous_status=(
                    change.previous_status.value if change.previous_status is not None else None
                ),
                status=change.status.value,
                previous_resolution_outcome=(
                    change.previous_resolution_outcome.value
                    if change.previous_resolution_outcome is not None
                    else None
                ),
                resolution_outcome=change.resolution_outcome.value,
                resolved_at=change.resolved_at,
                resolution_source=change.resolution_source,
            )
        )
        await self._session.flush()


def _provider_model(provider: Provider) -> ProviderModel:
    return ProviderModel(
        provider_id=provider.provider_id,
        code=provider.code,
        name=provider.name,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _provider_entity(model: ProviderModel) -> Provider:
    return Provider(
        provider_id=model.provider_id,
        code=model.code,
        name=model.name,
        enabled=model.enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _market_model(market: Market) -> MarketModel:
    return MarketModel(
        market_id=market.market_id,
        provider_id=market.provider_id,
        provider_market_id=market.provider_market_id,
        title=market.title,
        description=market.description,
        category=market.category,
        resolution_at=market.resolution_at,
        source_created_at=market.source_created_at,
        status=market.status.value,
        resolution_outcome=market.resolution_outcome.value,
        resolved_at=market.resolved_at,
        resolution_source=market.resolution_source,
        ingested_at=market.ingested_at,
        updated_at=market.updated_at,
    )


def _market_entity(model: MarketModel) -> Market:
    return Market(
        market_id=model.market_id,
        provider_id=model.provider_id,
        provider_market_id=model.provider_market_id,
        title=model.title,
        description=model.description,
        category=model.category,
        resolution_at=model.resolution_at,
        source_created_at=model.source_created_at,
        status=MarketStatus(model.status),
        resolution_outcome=ResolutionOutcome(model.resolution_outcome),
        resolved_at=model.resolved_at,
        resolution_source=model.resolution_source,
        ingested_at=model.ingested_at,
        updated_at=model.updated_at,
    )


def _snapshot_model(snapshot: MarketSnapshot) -> MarketSnapshotModel:
    return MarketSnapshotModel(**_snapshot_values(snapshot))


def _snapshot_values(snapshot: MarketSnapshot) -> dict[str, object]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "market_id": snapshot.market_id,
        "observed_at": snapshot.observed_at,
        "yes_price": snapshot.yes_price,
        "no_price": snapshot.no_price,
        "probability": snapshot.probability,
        "spread": snapshot.spread,
        "volume": snapshot.volume,
        "liquidity": snapshot.liquidity,
    }


def _snapshot_entity(model: MarketSnapshotModel) -> MarketSnapshot:
    return MarketSnapshot(
        snapshot_id=model.snapshot_id,
        market_id=model.market_id,
        observed_at=model.observed_at,
        yes_price=model.yes_price,
        no_price=model.no_price,
        probability=model.probability,
        spread=model.spread,
        volume=model.volume,
        liquidity=model.liquidity,
    )


def _observation_values(
    observation: MarketObservation,
) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id,
        "market_id": observation.market_id,
        "observed_at": observation.observed_at,
        "probability": observation.probability,
        "volume": observation.volume,
        "liquidity": observation.liquidity,
        "source_updated_at": observation.source_updated_at,
        "ingested_at": observation.ingested_at,
        "provider_code": observation.provider_code,
        "raw_payload_hash": observation.raw_payload_hash,
    }


def _observation_entity(
    model: MarketObservationModel,
) -> MarketObservation:
    return MarketObservation(
        observation_id=model.observation_id,
        market_id=model.market_id,
        observed_at=model.observed_at,
        probability=model.probability,
        volume=model.volume,
        liquidity=model.liquidity,
        source_updated_at=model.source_updated_at,
        ingested_at=model.ingested_at,
        provider_code=model.provider_code,
        raw_payload_hash=model.raw_payload_hash,
    )
