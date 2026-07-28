"""Read market state as it was visible at a prediction timestamp."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.application.predictions import MarketPredictionSnapshot
from predictionlab.domain.agents import AgentObservation
from predictionlab.domain.markets import MarketStatus
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
)


class SqlAlchemyPredictionMarketRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        observation_limit: int = 100,
    ) -> None:
        if observation_limit < 1:
            raise ValueError("observation_limit must be positive")
        self._session_factory = session_factory
        self._observation_limit = observation_limit

    async def get_as_of(
        self,
        market_id: UUID,
        predicted_at: datetime,
    ) -> MarketPredictionSnapshot | None:
        async with self._session_factory() as session:
            market = await session.scalar(
                select(MarketModel).where(
                    MarketModel.market_id == market_id,
                    MarketModel.ingested_at <= predicted_at,
                )
            )
            if market is None:
                return None
            state = await session.scalar(
                select(MarketStateChangeModel)
                .where(
                    MarketStateChangeModel.market_id == market_id,
                    MarketStateChangeModel.occurred_at <= predicted_at,
                )
                .order_by(
                    MarketStateChangeModel.occurred_at.desc(),
                    MarketStateChangeModel.change_id.desc(),
                )
                .limit(1)
            )
            if state is None:
                return None
            observations = (
                await session.scalars(
                    select(MarketObservationModel)
                    .where(
                        MarketObservationModel.market_id == market_id,
                        MarketObservationModel.observed_at <= predicted_at,
                    )
                    .order_by(
                        MarketObservationModel.observed_at.desc(),
                        MarketObservationModel.observation_id.desc(),
                    )
                    .limit(self._observation_limit)
                )
            ).all()
        ordered = tuple(
            AgentObservation(
                observed_at=item.observed_at,
                probability=item.probability,
                volume=item.volume,
                liquidity=item.liquidity,
            )
            for item in reversed(observations)
        )
        return MarketPredictionSnapshot(
            market_id=market.market_id,
            title=market.title,
            description=market.description,
            category=market.category,
            status=MarketStatus(state.status),
            resolution_at=market.resolution_at,
            observations=ordered,
        )

    async def list_open_ids_as_of(self, predicted_at: datetime) -> tuple[UUID, ...]:
        latest_status = (
            select(MarketStateChangeModel.status)
            .where(
                MarketStateChangeModel.market_id == MarketModel.market_id,
                MarketStateChangeModel.occurred_at <= predicted_at,
            )
            .order_by(
                MarketStateChangeModel.occurred_at.desc(),
                MarketStateChangeModel.change_id.desc(),
            )
            .limit(1)
            .correlate(MarketModel)
            .scalar_subquery()
        )
        async with self._session_factory() as session:
            ids = (
                await session.scalars(
                    select(MarketModel.market_id)
                    .where(
                        MarketModel.ingested_at <= predicted_at,
                        latest_status == MarketStatus.OPEN.value,
                    )
                    .order_by(MarketModel.market_id)
                )
            ).all()
        return tuple(ids)
