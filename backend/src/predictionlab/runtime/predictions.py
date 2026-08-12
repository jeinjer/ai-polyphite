"""Composition helpers for the deterministic prediction pipeline."""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.agents import (
    ConsensusAgent,
    HybridModelBackend,
    MarketAgent,
    ReasoningAgent,
    RuleBasedModelBackend,
    SkepticAgent,
)
from predictionlab.agents.ollama import OllamaModelBackend
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
    fallback = RuleBasedModelBackend()
    backend = (
        HybridModelBackend(
            ollama=OllamaModelBackend(
                base_url=str(settings.ollama_base_url),
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
                reasoning_temperature=settings.ollama_reasoning_temperature,
                skeptic_temperature=settings.ollama_skeptic_temperature,
            ),
            fallback=fallback,
            circuit_breaker_seconds=settings.ollama_circuit_breaker_seconds,
        )
        if settings.prediction_model_backend == "hybrid"
        else fallback
    )

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
        model_configuration_defaults={
            "model_backend": settings.prediction_model_backend,
            "ollama_model": (
                settings.ollama_model
                if settings.prediction_model_backend == "hybrid"
                else None
            ),
            "reasoning_prompt_version": "2.1.0",
            "skeptic_prompt_version": "2.1.0",
            "reasoning_temperature": str(settings.ollama_reasoning_temperature),
            "skeptic_temperature": str(settings.ollama_skeptic_temperature),
        },
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
        require_resolution_at=settings.prediction_require_resolution_at,
        minimum_resolution_horizon_seconds=(
            settings.prediction_minimum_resolution_horizon_seconds
        ),
        maximum_resolution_horizon_seconds=(
            settings.prediction_maximum_resolution_horizon_seconds
        ),
        maximum_candidates_per_batch=settings.prediction_maximum_candidates_per_batch,
    )
