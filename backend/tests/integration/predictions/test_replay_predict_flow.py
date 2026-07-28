from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    CollectorCheckpointModel,
    CollectorRunModel,
    ExperimentRunModel,
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PredictionRunModel,
    ProviderModel,
)
from predictionlab.runtime.prediction_replay import (
    PredictionReplayHook,
    ReplayPredictionSchedule,
)
from predictionlab.runtime.replay_runner import ReplayMode
from predictionlab.runtime.replay_runtime import create_replay_runtime

DATASET = Path(__file__).parents[3] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_replay_predict_persists_multiple_deterministic_timestamps() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        replay_dataset_directory=DATASET.parent,
    )
    provider_code = f"predict_replay_{uuid4().hex[:10]}"
    experiment_ids: list[UUID] = []
    hashes: list[str | None] = []
    prediction_counts: list[int] = []
    for _ in range(2):
        runtime = create_replay_runtime(
            settings,
            DATASET,
            provider_code=provider_code,
        )
        schedule = ReplayPredictionSchedule(
            replay_start=runtime.provider.metadata.replay_start,
            replay_end=runtime.provider.metadata.replay_end,
            interval=timedelta(days=5),
        )
        hook = PredictionReplayHook(
            orchestrator=runtime.prediction_orchestrator,
            schedule=schedule,
            random_seed=23,
        )
        try:
            execution = await runtime.runner.run(
                mode=ReplayMode.ACCELERATED,
                random_seed=23,
                artifact_hook=hook,
                extension_configuration={
                    "prediction_timestamps": [
                        item.isoformat() for item in schedule.timestamps
                    ]
                },
            )
            experiment_ids.append(execution.experiment.experiment_run_id)
            hashes.append(execution.experiment.result_hash)
            prediction_counts.append(hook.prediction_count)
            assert len(execution.artifact_hashes) == hook.prediction_count
        finally:
            await runtime.close()

    assert hashes[0] == hashes[1]
    assert prediction_counts[0] == prediction_counts[1]
    assert prediction_counts[0] > 1

    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            counts = [
                len(
                    (
                        await session.scalars(
                            select(PredictionRunModel).where(
                                PredictionRunModel.experiment_run_id == experiment_id
                            )
                        )
                    ).all()
                )
                for experiment_id in experiment_ids
            ]
        assert counts == prediction_counts
    finally:
        await _cleanup(session_factory, provider_code, experiment_ids)
        await engine.dispose()


async def _cleanup(
    session_factory,
    provider_code: str,
    experiment_ids: list[UUID],
) -> None:
    async with session_factory.begin() as session:
        prediction_ids = select(PredictionRunModel.prediction_run_id).where(
            PredictionRunModel.experiment_run_id.in_(experiment_ids)
        )
        await session.execute(
            delete(AgentPredictionModel).where(
                AgentPredictionModel.prediction_run_id.in_(prediction_ids)
            )
        )
        await session.execute(
            delete(PredictionRunModel).where(
                PredictionRunModel.experiment_run_id.in_(experiment_ids)
            )
        )
        provider_id = await session.scalar(
            select(ProviderModel.provider_id).where(
                ProviderModel.code == provider_code
            )
        )
        if provider_id is not None:
            market_ids = select(MarketModel.market_id).where(
                MarketModel.provider_id == provider_id
            )
            await session.execute(
                delete(MarketObservationModel).where(
                    MarketObservationModel.market_id.in_(market_ids)
                )
            )
            await session.execute(
                delete(MarketStateChangeModel).where(
                    MarketStateChangeModel.market_id.in_(market_ids)
                )
            )
            await session.execute(
                delete(MarketModel).where(MarketModel.provider_id == provider_id)
            )
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await session.execute(
            delete(CollectorCheckpointModel).where(
                CollectorCheckpointModel.provider_code == provider_code
            )
        )
        await session.execute(
            delete(CollectorRunModel).where(
                CollectorRunModel.provider_code == provider_code
            )
        )
        await session.execute(
            delete(ExperimentRunModel).where(
                ExperimentRunModel.experiment_run_id.in_(experiment_ids)
            )
        )
