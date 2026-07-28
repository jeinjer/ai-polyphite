from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from predictionlab.application.experiments import (
    ExperimentRunDetail,
    ExperimentRunPage,
    ListExperimentRuns,
)
from predictionlab.domain.experiments import ExperimentRunStatus
from predictionlab.infrastructure.database.models import ExperimentRunModel


class SqlAlchemyExperimentRunReadRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list(self, query: ListExperimentRuns) -> ExperimentRunPage:
        filters = _filters(query)
        async with self._session_factory() as session:
            total = (
                await session.scalar(
                    select(func.count()).select_from(ExperimentRunModel).where(*filters)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(ExperimentRunModel)
                    .where(*filters)
                    .order_by(
                        ExperimentRunModel.started_at.desc(),
                        ExperimentRunModel.experiment_run_id.asc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return ExperimentRunPage(
            items=tuple(_detail(row) for row in rows),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get(self, run_id: UUID) -> ExperimentRunDetail | None:
        async with self._session_factory() as session:
            row = await session.get(ExperimentRunModel, run_id)
        return _detail(row) if row is not None else None


def _filters(query: ListExperimentRuns) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if query.dataset_id is not None:
        filters.append(ExperimentRunModel.dataset_id == query.dataset_id.strip())
    if query.status is not None:
        filters.append(ExperimentRunModel.status == query.status.value)
    return tuple(filters)


def _detail(row: ExperimentRunModel) -> ExperimentRunDetail:
    status = ExperimentRunStatus(row.status)
    return ExperimentRunDetail(
        experiment_run_id=row.experiment_run_id,
        dataset_id=row.dataset_id,
        dataset_version=row.dataset_version,
        started_at=row.started_at,
        finished_at=row.finished_at,
        status=status,
        replay_start=row.replay_start,
        replay_end=row.replay_end,
        random_seed=row.random_seed,
        configuration_hash=row.configuration_hash,
        code_version=row.code_version,
        result_hash=row.result_hash,
        correlation_id=row.correlation_id,
        safe_error_type=row.safe_error_type,
        reproducible=status is ExperimentRunStatus.COMPLETED and row.result_hash is not None,
    )
