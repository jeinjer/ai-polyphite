from __future__ import annotations

import logging
from time import perf_counter
from uuid import UUID

from predictionlab.application.markets.errors import MarketNotFoundError
from predictionlab.application.markets.queries import (
    ListMarketHistory,
    ListMarketObservations,
    ListMarkets,
    MarketDetail,
    MarketHistoryPage,
    MarketObservationPage,
    MarketPage,
)
from predictionlab.application.markets.query_repository import MarketReadRepository

logger = logging.getLogger(__name__)


class MarketQueryService:
    def __init__(self, repository: MarketReadRepository) -> None:
        self._repository = repository

    async def list(self, query: ListMarkets) -> MarketPage:
        started_at = perf_counter()
        result = await self._repository.list(query)
        logger.info(
            "markets_queried",
            extra={
                "page": query.page,
                "page_size": query.page_size,
                "result_count": len(result.items),
                "total": result.total,
                "market_status": query.status.value if query.status else None,
                "provider_code": query.provider_code,
                "category": query.category,
                "order_by": query.order_by.value,
                "sort_direction": query.direction.value,
                "duration_ms": _duration_ms(started_at),
            },
        )
        return result

    async def get(self, market_id: UUID) -> MarketDetail:
        started_at = perf_counter()
        result = await self._repository.get(market_id)
        if result is None:
            logger.info(
                "market_query_not_found",
                extra={
                    "market_id": str(market_id),
                    "duration_ms": _duration_ms(started_at),
                },
            )
            raise MarketNotFoundError(str(market_id))

        logger.info(
            "market_queried",
            extra={
                "market_id": str(market_id),
                "duration_ms": _duration_ms(started_at),
            },
        )
        return result

    async def list_observations(
        self,
        query: ListMarketObservations,
    ) -> MarketObservationPage:
        started_at = perf_counter()
        result = await self._repository.list_observations(query)
        if result is None:
            raise MarketNotFoundError(str(query.market_id))
        logger.info(
            "market_observations_queried",
            extra={
                "market_id": str(query.market_id),
                "page": query.page,
                "result_count": len(result.items),
                "total": result.total,
                "duration_ms": _duration_ms(started_at),
            },
        )
        return result

    async def list_history(
        self,
        query: ListMarketHistory,
    ) -> MarketHistoryPage:
        started_at = perf_counter()
        result = await self._repository.list_history(query)
        if result is None:
            raise MarketNotFoundError(str(query.market_id))
        logger.info(
            "market_history_queried",
            extra={
                "market_id": str(query.market_id),
                "page": query.page,
                "result_count": len(result.items),
                "total": result.total,
                "duration_ms": _duration_ms(started_at),
            },
        )
        return result


def _duration_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
