"""Composition root for deterministic replay experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from predictionlab.application.markets import ServiceDependencies
from predictionlab.application.markets.unit_of_work import MarketUnitOfWork
from predictionlab.collectors import MarketDataCollector
from predictionlab.core.clock import ReplayClock
from predictionlab.core.settings import Settings
from predictionlab.infrastructure.database.collector_state import (
    PostgresProviderCollectionLock,
    SqlAlchemyCollectorCheckpointStore,
    SqlAlchemyCollectorRunStore,
)
from predictionlab.infrastructure.database.experiments import (
    SqlAlchemyExperimentRunStore,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.infrastructure.resources import (
    InfrastructureResources,
    create_resources,
)
from predictionlab.providers.replay import ReplayProvider, load_replay_dataset
from predictionlab.runtime.replay_runner import ReplayRunner


@dataclass(slots=True)
class ReplayRuntime:
    resources: InfrastructureResources
    provider: ReplayProvider
    clock: ReplayClock
    runner: ReplayRunner

    async def close(self) -> None:
        await self.resources.close()


def create_replay_runtime(
    settings: Settings,
    dataset_path: Path,
) -> ReplayRuntime:
    dataset = load_replay_dataset(dataset_path)
    clock = ReplayClock(
        start_at=dataset.metadata.replay_start,
        event_times=dataset.event_times,
    )
    provider = ReplayProvider(dataset_path, clock=clock)
    resources = create_resources(settings)

    def unit_of_work() -> MarketUnitOfWork:
        return cast(
            MarketUnitOfWork,
            SqlAlchemyMarketUnitOfWork(resources.session_factory),
        )

    dependencies = ServiceDependencies(
        unit_of_work=unit_of_work,
        clock=clock,
    )
    collector = MarketDataCollector(
        provider=provider,
        application_dependencies=dependencies,
        checkpoint_store=SqlAlchemyCollectorCheckpointStore(resources.session_factory),
        collection_lock=PostgresProviderCollectionLock(resources.database_engine),
        run_store=SqlAlchemyCollectorRunStore(resources.session_factory),
        clock=clock,
    )
    runner = ReplayRunner(
        metadata=provider.metadata,
        replay_clock=clock,
        collector=collector,
        experiment_store=SqlAlchemyExperimentRunStore(resources.session_factory),
        code_version=settings.code_version,
    )
    return ReplayRuntime(
        resources=resources,
        provider=provider,
        clock=clock,
        runner=runner,
    )
