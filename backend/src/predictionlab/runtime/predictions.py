"""Composition helpers for the deterministic prediction pipeline."""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.agents import (
    ConsensusAgent,
    MarketAgent,
    ReasoningAgent,
    RuleBasedModelBackend,
    SkepticAgent,
)
from predictionlab.application.predictions import (
    PredictionOrchestrator,
    PredictionUnitOfWork,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.settings import Settings
from predictionlab.domain.predictions import (
    EdgeThresholds,
    PredictionPolicy,
)
from predictionlab.infrastructure.database.prediction_unit_of_work import (
    SqlAlchemyPredictionUnitOfWork,
)
from predictionlab.infrastructure.database.queries import (
    SqlAlchemyPredictionMarketRepository,
)


def create_prediction_orchestrator(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    clock: Clock | None = None,
) -> PredictionOrchestrator:
    backend = RuleBasedModelBackend()

    def unit_of_work() -> PredictionUnitOfWork:
        return cast(
            PredictionUnitOfWork,
            SqlAlchemyPredictionUnitOfWork(session_factory),
        )

    return PredictionOrchestrator(
        market_repository=SqlAlchemyPredictionMarketRepository(session_factory),
        unit_of_work=unit_of_work,
        reasoning_agent=ReasoningAgent(backend),
        market_agent=MarketAgent(backend),
        skeptic_agent=SkepticAgent(backend),
        consensus_agent=ConsensusAgent(backend),
        policy=_policy(settings),
        clock=clock or SystemClock(),
    )


def _policy(settings: Settings) -> PredictionPolicy:
    return PredictionPolicy(
        edge_thresholds=EdgeThresholds(
            weak=settings.prediction_weak_edge,
            moderate=settings.prediction_moderate_edge,
            strong=settings.prediction_strong_edge,
        ),
        minimum_confidence=settings.prediction_minimum_confidence,
        maximum_disagreement=settings.prediction_maximum_disagreement,
        maximum_observation_age_seconds=(
            settings.prediction_maximum_observation_age_seconds
        ),
    )
