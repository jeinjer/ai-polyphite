from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from predictionlab.domain.markets import (
    Market,
    MarketObservation,
    MarketSnapshot,
    MarketStateChange,
    Provider,
)


@dataclass(frozen=True, slots=True)
class EntitySync[T]:
    entity: T
    created: bool
    updated: bool


@dataclass(frozen=True, slots=True)
class SnapshotWrite:
    snapshot: MarketSnapshot
    created: bool


@dataclass(frozen=True, slots=True)
class ObservationWrite:
    observation: MarketObservation
    created: bool


class ProviderRepository(Protocol):
    async def add(self, provider: Provider) -> None: ...

    async def update(self, provider: Provider) -> bool: ...

    async def get_by_id(self, provider_id: UUID) -> Provider | None: ...

    async def get_by_code(self, code: str) -> Provider | None: ...


class MarketRepository(Protocol):
    async def add(self, market: Market) -> None: ...

    async def update(self, market: Market) -> bool: ...

    async def get_by_id(self, market_id: UUID) -> Market | None: ...

    async def get_by_provider_reference(
        self,
        *,
        provider_id: UUID,
        provider_market_id: str,
    ) -> Market | None: ...


class MarketSnapshotRepository(Protocol):
    async def add(self, snapshot: MarketSnapshot) -> None: ...

    async def add_if_absent(self, snapshot: MarketSnapshot) -> SnapshotWrite: ...

    async def get_by_id(self, snapshot_id: UUID) -> MarketSnapshot | None: ...

    async def latest_for_market(self, market_id: UUID) -> MarketSnapshot | None: ...

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> Sequence[MarketSnapshot]: ...


class MarketObservationRepository(Protocol):
    async def add_if_absent(
        self,
        observation: MarketObservation,
    ) -> ObservationWrite: ...

    async def latest_for_market(
        self,
        market_id: UUID,
    ) -> MarketObservation | None: ...

    async def list_for_market(
        self,
        market_id: UUID,
        *,
        limit: int,
    ) -> Sequence[MarketObservation]: ...


class MarketStateHistoryRepository(Protocol):
    async def add(self, change: MarketStateChange) -> None: ...
