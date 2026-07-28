from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)
from predictionlab.collectors.models import CollectorRunStatus
from predictionlab.infrastructure.database.models import CollectorRunModel


class SqlAlchemyCollectorRunReadRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(self, query: ListCollectorRuns) -> CollectorRunPage:
        filters = _filters(query)
        async with self._session_factory() as session:
            total = (
                await session.scalar(
                    select(func.count()).select_from(CollectorRunModel).where(*filters)
                )
                or 0
            )
            models = (
                await session.scalars(
                    select(CollectorRunModel)
                    .where(*filters)
                    .order_by(
                        CollectorRunModel.started_at.desc(),
                        CollectorRunModel.run_id.asc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return CollectorRunPage(
            items=tuple(_detail(model) for model in models),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get(self, run_id: UUID) -> CollectorRunDetail | None:
        async with self._session_factory() as session:
            model = await session.get(CollectorRunModel, run_id)
        return _detail(model) if model is not None else None


def _filters(
    query: ListCollectorRuns,
) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if query.provider_code is not None:
        filters.append(CollectorRunModel.provider_code == query.provider_code.strip())
    if query.status is not None:
        filters.append(CollectorRunModel.status == query.status.value)
    if query.started_from is not None:
        filters.append(CollectorRunModel.started_at >= query.started_from)
    if query.started_to is not None:
        filters.append(CollectorRunModel.started_at <= query.started_to)
    return tuple(filters)


def _detail(model: CollectorRunModel) -> CollectorRunDetail:
    return CollectorRunDetail(
        run_id=model.run_id,
        provider_code=model.provider_code,
        started_at=model.started_at,
        finished_at=model.finished_at,
        status=CollectorRunStatus(model.status),
        markets_fetched=model.markets_fetched,
        markets_created=model.markets_created,
        markets_updated=model.markets_updated,
        markets_unchanged=model.markets_unchanged,
        observations_fetched=model.observations_fetched,
        observations_created=model.observations_created,
        observations_duplicated=model.observations_duplicated,
        observations_skipped=model.observations_skipped,
        retry_count=model.retry_count,
        duration_ms=model.duration_ms,
        safe_error_type=model.safe_error_type,
        correlation_id=model.correlation_id,
    )
