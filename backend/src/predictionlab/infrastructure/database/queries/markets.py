from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import (
    Numeric,
    Select,
    String,
    func,
    literal,
    null,
    select,
    union_all,
)
from sqlalchemy import (
    cast as sql_cast,
)
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from predictionlab.application.markets.queries import (
    ListMarketHistory,
    ListMarketObservations,
    ListMarkets,
    MarketDetail,
    MarketHistoryEvent,
    MarketHistoryEventType,
    MarketHistoryPage,
    MarketObservationPage,
    MarketOrderField,
    MarketPage,
    MarketSummary,
    ObservationSummary,
    ProviderSummary,
    SnapshotSummary,
    SortDirection,
)
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)

type MarketRow = Row[
    tuple[
        MarketModel,
        ProviderModel,
        MarketSnapshotModel,
        MarketObservationModel,
        Decimal | None,
    ]
]


class SqlAlchemyMarketReadRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(self, query: ListMarkets) -> MarketPage:
        filters = _filters(query)
        async with self._session_factory() as session:
            total = (
                await session.scalar(
                    select(func.count())
                    .select_from(MarketModel)
                    .join(
                        ProviderModel,
                        ProviderModel.provider_id == MarketModel.provider_id,
                    )
                    .where(*filters)
                )
                or 0
            )
            rows = (
                await session.execute(
                    _market_select()
                    .where(*filters)
                    .order_by(*_ordering(query))
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()

        return MarketPage(
            items=tuple(_summary(row) for row in rows),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get(self, market_id: UUID) -> MarketDetail | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(_market_select().where(MarketModel.market_id == market_id))
            ).one_or_none()
        return _detail(row) if row is not None else None

    async def list_observations(
        self,
        query: ListMarketObservations,
    ) -> MarketObservationPage | None:
        filters = [MarketObservationModel.market_id == query.market_id]
        if query.observed_from is not None:
            filters.append(MarketObservationModel.observed_at >= query.observed_from)
        if query.observed_to is not None:
            filters.append(MarketObservationModel.observed_at <= query.observed_to)
        async with self._session_factory() as session:
            if not await _market_exists(session, query.market_id):
                return None
            total = (
                await session.scalar(
                    select(func.count()).select_from(MarketObservationModel).where(*filters)
                )
                or 0
            )
            models = (
                await session.scalars(
                    select(MarketObservationModel)
                    .where(*filters)
                    .order_by(
                        MarketObservationModel.observed_at.desc(),
                        MarketObservationModel.observation_id.desc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return MarketObservationPage(
            items=tuple(cast(ObservationSummary, _observation(model)) for model in models),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def list_history(
        self,
        query: ListMarketHistory,
    ) -> MarketHistoryPage | None:
        history = _history_union(query.market_id)
        async with self._session_factory() as session:
            if not await _market_exists(session, query.market_id):
                return None
            total = await session.scalar(select(func.count()).select_from(history)) or 0
            rows = (
                await session.execute(
                    select(history)
                    .order_by(
                        history.c.occurred_at.desc(),
                        history.c.event_type.asc(),
                        history.c.event_id.asc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return MarketHistoryPage(
            items=tuple(_history_event(row) for row in rows),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )


def _market_select() -> Select[
    tuple[
        MarketModel,
        ProviderModel,
        MarketSnapshotModel,
        MarketObservationModel,
        Decimal | None,
    ]
]:
    latest_snapshot_id = (
        select(MarketSnapshotModel.snapshot_id)
        .where(MarketSnapshotModel.market_id == MarketModel.market_id)
        .order_by(
            MarketSnapshotModel.observed_at.desc(),
            MarketSnapshotModel.snapshot_id.desc(),
        )
        .limit(1)
        .correlate(MarketModel)
        .scalar_subquery()
    )
    latest_observation_id = (
        select(MarketObservationModel.observation_id)
        .where(MarketObservationModel.market_id == MarketModel.market_id)
        .order_by(
            MarketObservationModel.observed_at.desc(),
            MarketObservationModel.observation_id.desc(),
        )
        .limit(1)
        .correlate(MarketModel)
        .scalar_subquery()
    )
    previous_probability = (
        select(MarketObservationModel.probability)
        .where(MarketObservationModel.market_id == MarketModel.market_id)
        .order_by(
            MarketObservationModel.observed_at.desc(),
            MarketObservationModel.observation_id.desc(),
        )
        .offset(1)
        .limit(1)
        .correlate(MarketModel)
        .scalar_subquery()
        .label("previous_probability")
    )
    return (
        select(
            MarketModel,
            ProviderModel,
            MarketSnapshotModel,
            MarketObservationModel,
            previous_probability,
        )
        .join(
            ProviderModel,
            ProviderModel.provider_id == MarketModel.provider_id,
        )
        .outerjoin(
            MarketSnapshotModel,
            MarketSnapshotModel.snapshot_id == latest_snapshot_id,
        )
        .outerjoin(
            MarketObservationModel,
            MarketObservationModel.observation_id == latest_observation_id,
        )
    )


def _filters(query: ListMarkets) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if query.status is not None:
        filters.append(MarketModel.status == query.status.value)
    if query.provider_code is not None:
        filters.append(ProviderModel.code == query.provider_code.strip())
    if query.category is not None:
        filters.append(MarketModel.category == query.category.strip())
    return tuple(filters)


def _ordering(query: ListMarkets) -> tuple[ColumnElement[Any], ...]:
    column: InstrumentedAttribute[Any]
    if query.order_by is MarketOrderField.INGESTED_AT:
        column = MarketModel.ingested_at
    elif query.order_by is MarketOrderField.RESOLUTION_AT:
        column = MarketModel.resolution_at
    elif query.order_by is MarketOrderField.TITLE:
        column = MarketModel.title
    else:
        column = MarketModel.updated_at

    primary = column.asc() if query.direction is SortDirection.ASC else column.desc()
    if query.order_by is MarketOrderField.RESOLUTION_AT:
        primary = primary.nulls_last()
    return (primary, MarketModel.market_id.asc())


def _provider(model: ProviderModel) -> ProviderSummary:
    return ProviderSummary(
        provider_id=model.provider_id,
        code=model.code,
        name=model.name,
        enabled=model.enabled,
    )


def _snapshot(model: MarketSnapshotModel | None) -> SnapshotSummary | None:
    if model is None:
        return None
    return SnapshotSummary(
        snapshot_id=model.snapshot_id,
        observed_at=model.observed_at,
        yes_price=model.yes_price,
        no_price=model.no_price,
        probability=model.probability,
        spread=model.spread,
        volume=model.volume,
        liquidity=model.liquidity,
    )


def _observation(
    model: MarketObservationModel | None,
) -> ObservationSummary | None:
    if model is None:
        return None
    return ObservationSummary(
        observation_id=model.observation_id,
        observed_at=model.observed_at,
        probability=model.probability,
        volume=model.volume,
        liquidity=model.liquidity,
        source_updated_at=model.source_updated_at,
        ingested_at=model.ingested_at,
        provider_code=model.provider_code,
    )


def _summary(row: MarketRow) -> MarketSummary:
    market, provider, snapshot, observation, previous_probability = row
    latest_observation = _observation(cast(MarketObservationModel | None, observation))
    return MarketSummary(
        market_id=market.market_id,
        provider_market_id=market.provider_market_id,
        title=market.title,
        category=market.category,
        resolution_at=market.resolution_at,
        source_created_at=market.source_created_at,
        status=MarketStatus(market.status),
        ingested_at=market.ingested_at,
        updated_at=market.updated_at,
        provider=_provider(provider),
        latest_snapshot=_snapshot(cast(MarketSnapshotModel | None, snapshot)),
        resolution_outcome=ResolutionOutcome(market.resolution_outcome),
        resolved_at=market.resolved_at,
        resolution_source=market.resolution_source,
        latest_observation=latest_observation,
        probability_change=_probability_change(
            latest_observation,
            previous_probability,
        ),
    )


def _detail(row: MarketRow) -> MarketDetail:
    market, provider, snapshot, observation, previous_probability = row
    latest_observation = _observation(cast(MarketObservationModel | None, observation))
    return MarketDetail(
        market_id=market.market_id,
        provider_market_id=market.provider_market_id,
        title=market.title,
        description=market.description,
        category=market.category,
        resolution_at=market.resolution_at,
        source_created_at=market.source_created_at,
        status=MarketStatus(market.status),
        ingested_at=market.ingested_at,
        updated_at=market.updated_at,
        provider=_provider(provider),
        latest_snapshot=_snapshot(cast(MarketSnapshotModel | None, snapshot)),
        resolution_outcome=ResolutionOutcome(market.resolution_outcome),
        resolved_at=market.resolved_at,
        resolution_source=market.resolution_source,
        latest_observation=latest_observation,
        probability_change=_probability_change(
            latest_observation,
            previous_probability,
        ),
    )


async def _market_exists(session: AsyncSession, market_id: UUID) -> bool:
    return (
        await session.scalar(
            select(MarketModel.market_id).where(MarketModel.market_id == market_id)
        )
        is not None
    )


def _history_union(market_id: UUID) -> Subquery:
    no_text = sql_cast(null(), String)
    no_decimal = sql_cast(null(), Numeric(28, 10))

    def market_event(
        event_type: str,
        timestamp: InstrumentedAttribute[Any],
        suffix: str,
    ) -> Select[Any]:
        return select(
            (sql_cast(MarketModel.market_id, String) + literal(f":{suffix}")).label("event_id"),
            literal(event_type).label("event_type"),
            timestamp.label("occurred_at"),
            no_text.label("previous_status"),
            MarketModel.status.label("status"),
            MarketModel.resolution_outcome.label("resolution_outcome"),
            no_decimal.label("probability"),
            no_decimal.label("volume"),
            no_decimal.label("liquidity"),
            no_text.label("source"),
        ).where(
            MarketModel.market_id == market_id,
            timestamp.is_not(None),
        )

    source_created = market_event(
        MarketHistoryEventType.SOURCE_CREATED.value,
        MarketModel.source_created_at,
        "source-created",
    )
    ingested = market_event(
        MarketHistoryEventType.INGESTED.value,
        MarketModel.ingested_at,
        "ingested",
    )
    scheduled_close = market_event(
        MarketHistoryEventType.SCHEDULED_CLOSE.value,
        MarketModel.resolution_at,
        "scheduled-close",
    )
    resolution = select(
        (sql_cast(MarketModel.market_id, String) + literal(":resolution")).label("event_id"),
        literal(MarketHistoryEventType.RESOLUTION.value).label("event_type"),
        MarketModel.resolved_at.label("occurred_at"),
        no_text.label("previous_status"),
        MarketModel.status.label("status"),
        MarketModel.resolution_outcome.label("resolution_outcome"),
        no_decimal.label("probability"),
        no_decimal.label("volume"),
        no_decimal.label("liquidity"),
        MarketModel.resolution_source.label("source"),
    ).where(
        MarketModel.market_id == market_id,
        MarketModel.resolved_at.is_not(None),
    )
    state_changes = select(
        sql_cast(MarketStateChangeModel.change_id, String).label("event_id"),
        literal(MarketHistoryEventType.STATE_CHANGED.value).label("event_type"),
        MarketStateChangeModel.occurred_at.label("occurred_at"),
        MarketStateChangeModel.previous_status.label("previous_status"),
        MarketStateChangeModel.status.label("status"),
        MarketStateChangeModel.resolution_outcome.label("resolution_outcome"),
        no_decimal.label("probability"),
        no_decimal.label("volume"),
        no_decimal.label("liquidity"),
        MarketStateChangeModel.resolution_source.label("source"),
    ).where(MarketStateChangeModel.market_id == market_id)
    observations = select(
        sql_cast(MarketObservationModel.observation_id, String).label("event_id"),
        literal(MarketHistoryEventType.OBSERVATION.value).label("event_type"),
        MarketObservationModel.observed_at.label("occurred_at"),
        no_text.label("previous_status"),
        no_text.label("status"),
        no_text.label("resolution_outcome"),
        MarketObservationModel.probability.label("probability"),
        MarketObservationModel.volume.label("volume"),
        MarketObservationModel.liquidity.label("liquidity"),
        MarketObservationModel.provider_code.label("source"),
    ).where(MarketObservationModel.market_id == market_id)
    return union_all(
        source_created,
        ingested,
        scheduled_close,
        resolution,
        state_changes,
        observations,
    ).subquery("market_history")


def _history_event(row: Row[Any]) -> MarketHistoryEvent:
    return MarketHistoryEvent(
        event_id=str(row.event_id),
        event_type=MarketHistoryEventType(str(row.event_type)),
        occurred_at=cast(Any, row.occurred_at),
        previous_status=(
            MarketStatus(str(row.previous_status)) if row.previous_status is not None else None
        ),
        status=(MarketStatus(str(row.status)) if row.status is not None else None),
        resolution_outcome=(
            ResolutionOutcome(str(row.resolution_outcome))
            if row.resolution_outcome is not None
            else None
        ),
        probability=cast(Any, row.probability),
        volume=cast(Any, row.volume),
        liquidity=cast(Any, row.liquidity),
        source=cast(str | None, row.source),
    )


def _probability_change(
    latest: ObservationSummary | None,
    previous: Decimal | None,
) -> Decimal | None:
    if latest is None or latest.probability is None or previous is None:
        return None
    return latest.probability - previous
