from __future__ import annotations

from typing import Protocol
from uuid import UUID

from predictionlab.application.markets.queries import (
    ListMarketHistory,
    ListMarketObservations,
    ListMarkets,
    MarketDetail,
    MarketHistoryPage,
    MarketObservationPage,
    MarketPage,
)


class MarketReadRepository(Protocol):
    async def list(self, query: ListMarkets) -> MarketPage: ...

    async def get(self, market_id: UUID) -> MarketDetail | None: ...

    async def list_observations(
        self,
        query: ListMarketObservations,
    ) -> MarketObservationPage | None: ...

    async def list_history(
        self,
        query: ListMarketHistory,
    ) -> MarketHistoryPage | None: ...
