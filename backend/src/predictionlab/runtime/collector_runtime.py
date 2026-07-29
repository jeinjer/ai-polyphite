"""Composition root shared by the collector CLI and worker process."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

from predictionlab.application.markets import ServiceDependencies
from predictionlab.application.markets.unit_of_work import MarketUnitOfWork
from predictionlab.collectors import CollectorConfig, MarketDataCollector
from predictionlab.core.settings import Settings
from predictionlab.infrastructure.database.collector_state import (
    PostgresProviderCollectionLock,
    SqlAlchemyCollectorCheckpointStore,
    SqlAlchemyCollectorRunStore,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.infrastructure.resources import (
    InfrastructureResources,
    create_resources,
)
from predictionlab.providers.base import MarketDataProvider
from predictionlab.runtime.collector_worker import CollectorWorker
from predictionlab.runtime.providers import create_configured_provider_registry


@dataclass(slots=True)
class CollectorRuntime:
    resources: InfrastructureResources
    providers: tuple[MarketDataProvider, ...]
    worker: CollectorWorker

    async def close(self) -> None:
        await asyncio.gather(*(_close_provider(provider) for provider in self.providers))
        await self.resources.close()


def create_collector_runtime(settings: Settings) -> CollectorRuntime:
    registry = create_configured_provider_registry(settings)
    resources = create_resources(settings)
    providers = registry.create_all()

    def unit_of_work() -> MarketUnitOfWork:
        return cast(
            MarketUnitOfWork,
            SqlAlchemyMarketUnitOfWork(resources.session_factory),
        )

    dependencies = ServiceDependencies(unit_of_work=unit_of_work)
    checkpoint_store = SqlAlchemyCollectorCheckpointStore(resources.session_factory)
    run_store = SqlAlchemyCollectorRunStore(resources.session_factory)
    collection_lock = PostgresProviderCollectionLock(resources.database_engine)
    collectors = {
        provider.code: MarketDataCollector(
            provider=provider,
            application_dependencies=dependencies,
            checkpoint_store=checkpoint_store,
            collection_lock=collection_lock,
            run_store=run_store,
            config=CollectorConfig(
                page_size=settings.collector_page_size,
                max_pages_per_run=settings.collector_max_pages_per_run,
                collect_latest_snapshots=True,
                collect_latest_observations=True,
            ),
        )
        for provider in providers
    }
    worker = CollectorWorker(
        collectors=collectors,
        intervals_seconds={code: settings.provider_interval(code) for code in collectors},
        run_immediately=settings.collector_run_immediately,
    )
    return CollectorRuntime(
        resources=resources,
        providers=providers,
        worker=worker,
    )


async def _close_provider(provider: MarketDataProvider) -> None:
    close = getattr(provider, "aclose", None)
    if close is not None:
        await close()
