from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from predictionlab.application.markets.repositories import (
    MarketObservationRepository,
    MarketRepository,
    MarketSnapshotRepository,
    MarketStateHistoryRepository,
    ProviderRepository,
)


class MarketUnitOfWork(Protocol):
    providers: ProviderRepository
    markets: MarketRepository
    snapshots: MarketSnapshotRepository
    observations: MarketObservationRepository
    market_history: MarketStateHistoryRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


type MarketUnitOfWorkFactory = Callable[[], MarketUnitOfWork]
