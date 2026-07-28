from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Lifespan

from predictionlab.api.middleware.request_context import RequestContextMiddleware
from predictionlab.api.routes.collector_runs import router as collector_runs_router
from predictionlab.api.routes.experiments import router as experiments_router
from predictionlab.api.routes.health import router as health_router
from predictionlab.api.routes.markets import router as markets_router
from predictionlab.api.routes.sources import router as sources_router
from predictionlab.application.collectors.service import CollectorRunQueryService
from predictionlab.application.experiments import (
    ExperimentRunQueryService,
    ReplayDatasetQueryService,
)
from predictionlab.application.markets.query_service import MarketQueryService
from predictionlab.application.sources import SourceHealthQueryService
from predictionlab.core.logging import configure_logging
from predictionlab.core.settings import Settings, get_settings
from predictionlab.infrastructure.database.queries import (
    SqlAlchemyCollectorRunReadRepository,
    SqlAlchemyExperimentRunReadRepository,
    SqlAlchemyMarketReadRepository,
)
from predictionlab.infrastructure.observability.http_metrics import HttpRequestMetrics
from predictionlab.infrastructure.replay import FileReplayDatasetCatalog
from predictionlab.infrastructure.resources import create_resources
from predictionlab.runtime.providers import (
    ProviderSourceHealthRepository,
    create_configured_provider_registry,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title="AI-Polyphite API",
        description="Experimental prediction-market research platform.",
        version="0.1.0",
        lifespan=_build_lifespan(resolved_settings),
    )
    application.state.settings = resolved_settings
    request_metrics = HttpRequestMetrics()
    application.state.request_metrics = request_metrics

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware, metrics=request_metrics)
    application.include_router(health_router)
    application.include_router(markets_router)
    application.include_router(collector_runs_router)
    application.include_router(sources_router)
    application.include_router(experiments_router)
    return application


def _build_lifespan(settings: Settings) -> Lifespan[FastAPI]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resources = create_resources(settings)
        application.state.resources = resources
        application.state.readiness_checker = resources.readiness
        application.state.market_query_service = MarketQueryService(
            SqlAlchemyMarketReadRepository(resources.session_factory)
        )
        application.state.collector_run_query_service = CollectorRunQueryService(
            SqlAlchemyCollectorRunReadRepository(resources.session_factory)
        )
        application.state.experiment_run_query_service = ExperimentRunQueryService(
            SqlAlchemyExperimentRunReadRepository(resources.session_factory)
        )
        application.state.replay_dataset_query_service = ReplayDatasetQueryService(
            FileReplayDatasetCatalog(settings.replay_dataset_directory)
        )
        application.state.source_health_service = SourceHealthQueryService(
            ProviderSourceHealthRepository(create_configured_provider_registry(settings))
        )
        logger.info(
            "application_started",
            extra={"configuration": settings.safe_summary()},
        )

        try:
            yield
        finally:
            await resources.close()
            logger.info("application_stopped")

    return lifespan


app = create_app()
