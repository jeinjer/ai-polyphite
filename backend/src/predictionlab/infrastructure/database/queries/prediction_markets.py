"""Read market state as it was visible at a prediction timestamp."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.application.predictions import MarketPredictionSnapshot
from predictionlab.domain.agents import AgentObservation
from predictionlab.domain.markets import MarketStatus
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PredictionRunModel,
    ProviderModel,
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

    async def list_open_ids_as_of(
        self,
        predicted_at: datetime,
        *,
        provider_codes: tuple[str, ...] = (),
        only_with_new_observations: bool = False,
        require_resolution_at: bool = False,
        minimum_resolution_horizon_seconds: int = 0,
        maximum_resolution_horizon_seconds: int | None = None,
        agent_configuration_hash: str | None = None,
        limit: int | None = None,
    ) -> tuple[UUID, ...]:
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
        statement = select(MarketModel.market_id).where(
            MarketModel.ingested_at <= predicted_at,
            latest_status == MarketStatus.OPEN.value,
        )
        if require_resolution_at:
            statement = statement.where(MarketModel.resolution_at.is_not(None))
        if minimum_resolution_horizon_seconds:
            statement = statement.where(
                MarketModel.resolution_at
                > predicted_at + timedelta(seconds=minimum_resolution_horizon_seconds)
            )
        if maximum_resolution_horizon_seconds is not None:
            statement = statement.where(
                MarketModel.resolution_at
                <= predicted_at + timedelta(seconds=maximum_resolution_horizon_seconds)
            )
        if provider_codes:
            statement = statement.join(
                ProviderModel,
                ProviderModel.provider_id == MarketModel.provider_id,
            ).where(ProviderModel.code.in_(provider_codes))
        if only_with_new_observations:
            latest_observation = (
                select(func.max(MarketObservationModel.observed_at))
                .where(
                    MarketObservationModel.market_id == MarketModel.market_id,
                    MarketObservationModel.observed_at <= predicted_at,
                )
                .correlate(MarketModel)
                .scalar_subquery()
            )
            latest_live_prediction = (
                select(func.max(PredictionRunModel.predicted_at))
                .where(
                    PredictionRunModel.market_id == MarketModel.market_id,
                    PredictionRunModel.experiment_run_id.is_(None),
                    PredictionRunModel.predicted_at <= predicted_at,
                    *(
                        (
                            PredictionRunModel.agent_configuration_hash
                            == agent_configuration_hash,
                        )
                        if agent_configuration_hash is not None
                        else ()
                    ),
                )
                .correlate(MarketModel)
                .scalar_subquery()
            )
            statement = statement.where(
                latest_observation.is_not(None),
                or_(
                    latest_live_prediction.is_(None),
                    latest_observation > latest_live_prediction,
                ),
            )
        statement = statement.order_by(
            MarketModel.resolution_at.asc().nulls_last(),
            MarketModel.market_id,
        )
        if limit is not None:
            statement = statement.limit(limit)
        async with self._session_factory() as session:
            ids = (
                await session.scalars(statement)
            ).all()
        return tuple(ids)
