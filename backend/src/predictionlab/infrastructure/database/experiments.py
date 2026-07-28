"""SQLAlchemy write adapter for experiment runs."""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.domain.experiments import ExperimentRun
from predictionlab.infrastructure.database.models import ExperimentRunModel


class SqlAlchemyExperimentRunStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def start(self, run: ExperimentRun) -> None:
        async with self._session_factory.begin() as session:
            session.add(_model(run))

    async def finish(self, run: ExperimentRun) -> None:
        async with self._session_factory.begin() as session:
            updated_id = await session.scalar(
                update(ExperimentRunModel)
                .where(ExperimentRunModel.experiment_run_id == run.experiment_run_id)
                .values(
                    finished_at=run.finished_at,
                    status=run.status.value,
                    replay_end=run.replay_end,
                    result_hash=run.result_hash,
                    safe_error_type=run.safe_error_type,
                )
                .returning(ExperimentRunModel.experiment_run_id)
            )
            if updated_id is None:
                raise RuntimeError("experiment run disappeared before completion")


def _model(run: ExperimentRun) -> ExperimentRunModel:
    return ExperimentRunModel(
        experiment_run_id=run.experiment_run_id,
        dataset_id=run.dataset_id,
        dataset_version=run.dataset_version,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status.value,
        replay_start=run.replay_start,
        replay_end=run.replay_end,
        random_seed=run.random_seed,
        configuration_hash=run.configuration_hash,
        code_version=run.code_version,
        result_hash=run.result_hash,
        correlation_id=run.correlation_id,
        safe_error_type=run.safe_error_type,
    )
