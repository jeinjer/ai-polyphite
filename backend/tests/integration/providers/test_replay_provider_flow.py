from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.markets import ServiceDependencies
from predictionlab.application.markets.unit_of_work import MarketUnitOfWork
from predictionlab.collectors import MarketDataCollector
from predictionlab.core.clock import ReplayClock
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.collector_state import (
    PostgresProviderCollectionLock,
    SqlAlchemyCollectorCheckpointStore,
    SqlAlchemyCollectorRunStore,
)
from predictionlab.infrastructure.database.experiments import (
    SqlAlchemyExperimentRunStore,
)
from predictionlab.infrastructure.database.models import (
    CollectorCheckpointModel,
    CollectorRunModel,
    ExperimentRunModel,
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.providers.replay import ReplayProvider, load_replay_dataset
from predictionlab.runtime.replay_runner import ReplayMode, ReplayRunner

DATASET = Path(__file__).parents[3] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_replay_collector_is_deterministic_and_reaches_api() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        replay_dataset_directory=DATASET.parent,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    dataset = load_replay_dataset(DATASET)
    provider_code = f"replay_{uuid4().hex[:12]}"
    experiment_ids = []

    def create_runner() -> ReplayRunner:
        clock = ReplayClock(
            start_at=dataset.metadata.replay_start,
            event_times=dataset.event_times,
        )
        provider = ReplayProvider(DATASET, clock=clock, code=provider_code)

        def unit_of_work() -> MarketUnitOfWork:
            return cast(
                MarketUnitOfWork,
                SqlAlchemyMarketUnitOfWork(session_factory),
            )

        collector = MarketDataCollector(
            provider=provider,
            application_dependencies=ServiceDependencies(
                unit_of_work=unit_of_work,
                clock=clock,
            ),
            checkpoint_store=SqlAlchemyCollectorCheckpointStore(session_factory),
            run_store=SqlAlchemyCollectorRunStore(session_factory),
            collection_lock=PostgresProviderCollectionLock(engine),
            clock=clock,
        )
        return ReplayRunner(
            metadata=dataset.metadata,
            replay_clock=clock,
            collector=collector,
            experiment_store=SqlAlchemyExperimentRunStore(session_factory),
            code_version="integration-test",
        )

    try:
        first = await create_runner().run(
            mode=ReplayMode.ACCELERATED,
            random_seed=17,
        )
        experiment_ids.append(first.experiment.experiment_run_id)
        first_hash = await _persistence_hash(session_factory, provider_code)

        second = await create_runner().run(
            mode=ReplayMode.ACCELERATED,
            random_seed=17,
        )
        experiment_ids.append(second.experiment.experiment_run_id)
        second_hash = await _persistence_hash(session_factory, provider_code)

        assert first.experiment.result_hash == second.experiment.result_hash
        assert first_hash == second_hash

        async with session_factory() as session:
            provider_id = await session.scalar(
                select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
            )
            assert provider_id is not None
            market_count = await session.scalar(
                select(func.count())
                .select_from(MarketModel)
                .where(MarketModel.provider_id == provider_id)
            )
            observation_count = await session.scalar(
                select(func.count())
                .select_from(MarketObservationModel)
                .join(MarketModel)
                .where(MarketModel.provider_id == provider_id)
            )
            state_count = await session.scalar(
                select(func.count())
                .select_from(MarketStateChangeModel)
                .join(MarketModel)
                .where(MarketModel.provider_id == provider_id)
            )
        assert market_count == 20
        assert observation_count == 80
        assert state_count == 60

        application = create_app(settings)
        async with application.router.lifespan_context(application), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        ) as client:
            markets = await client.get(
                "/markets",
                params={"provider": provider_code, "page_size": 100},
            )
            experiments = await client.get(
                "/experiment-runs",
                params={"dataset": "synthetic-lab", "page_size": 10},
            )
            detail = await client.get(
                f"/experiment-runs/{first.experiment.experiment_run_id}"
            )
            datasets = await client.get("/replay-datasets")

        assert markets.status_code == 200
        assert markets.json()["total"] == 20
        assert experiments.status_code == 200
        assert experiments.json()["total"] >= 2
        assert detail.json()["reproducible"] is True
        assert datasets.json()[0]["content_sha256"] == dataset.metadata.content_sha256
    finally:
        await _cleanup(
            session_factory,
            provider_code=provider_code,
            experiment_ids=experiment_ids,
        )
        await engine.dispose()


async def _persistence_hash(
    session_factory: async_sessionmaker[AsyncSession],
    provider_code: str,
) -> str:
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(
                    MarketModel.provider_market_id,
                    MarketModel.status,
                    MarketModel.resolution_outcome,
                    MarketObservationModel.observed_at,
                    MarketObservationModel.probability,
                    MarketObservationModel.volume,
                    MarketObservationModel.liquidity,
                )
                .join(
                    ProviderModel,
                    ProviderModel.provider_id == MarketModel.provider_id,
                )
                .join(
                    MarketObservationModel,
                    MarketObservationModel.market_id == MarketModel.market_id,
                )
                .where(ProviderModel.code == provider_code)
                .order_by(
                    MarketModel.provider_market_id,
                    MarketObservationModel.observed_at,
                )
            )
        ).all()
    canonical = json.dumps(
        [[str(value) for value in row] for row in rows],
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


async def _cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    provider_code: str,
    experiment_ids: list[UUID],
) -> None:
    async with session_factory.begin() as session:
        provider_id = await session.scalar(
            select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
        )
        if provider_id is not None:
            market_ids = select(MarketModel.market_id).where(
                MarketModel.provider_id == provider_id
            )
            await session.execute(
                delete(MarketSnapshotModel).where(MarketSnapshotModel.market_id.in_(market_ids))
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
            await session.execute(delete(MarketModel).where(MarketModel.provider_id == provider_id))
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await session.execute(
            delete(CollectorCheckpointModel).where(
                CollectorCheckpointModel.provider_code == provider_code
            )
        )
        await session.execute(
            delete(CollectorRunModel).where(CollectorRunModel.provider_code == provider_code)
        )
        if experiment_ids:
            await session.execute(
                delete(ExperimentRunModel).where(
                    ExperimentRunModel.experiment_run_id.in_(experiment_ids)
                )
            )
