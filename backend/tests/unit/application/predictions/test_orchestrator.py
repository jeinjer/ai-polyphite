from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from predictionlab.agents import (
    ConsensusAgent,
    MarketAgent,
    ReasoningAgent,
    RuleBasedModelBackend,
    SkepticAgent,
)
from predictionlab.application.predictions import (
    MarketPredictionSnapshot,
    PredictionOrchestrator,
    RunPrediction,
)
from predictionlab.domain.agents import AgentObservation
from predictionlab.domain.markets import MarketStatus
from predictionlab.domain.predictions import PredictionRun

NOW = datetime(2026, 1, 5, tzinfo=UTC)
MARKET_ID = UUID("00000000-0000-4000-8000-000000000610")


class FixedClock:
    def now(self) -> datetime:
        return NOW

    def __call__(self) -> datetime:
        return self.now()


class MemoryMarketRepository:
    async def get_as_of(
        self,
        market_id: UUID,
        predicted_at: datetime,
    ) -> MarketPredictionSnapshot | None:
        if market_id != MARKET_ID:
            return None
        return MarketPredictionSnapshot(
            market_id=market_id,
            title="Mercado reproducible",
            description="Contexto sintético.",
            category="testing",
            status=MarketStatus.OPEN,
            resolution_at=NOW + timedelta(days=2),
            observations=(
                AgentObservation(
                    observed_at=NOW - timedelta(hours=2),
                    probability=Decimal("0.45"),
                    volume=Decimal("100"),
                    liquidity=Decimal("50"),
                ),
                AgentObservation(
                    observed_at=NOW,
                    probability=Decimal("0.55"),
                    volume=Decimal("120"),
                    liquidity=Decimal("55"),
                ),
            ),
        )

    async def list_open_ids_as_of(
        self,
        predicted_at: datetime,
        *,
        provider_codes: tuple[str, ...] = (),
        only_with_new_observations: bool = False,
    ) -> tuple[UUID, ...]:
        del predicted_at, provider_codes, only_with_new_observations
        return (MARKET_ID,)


class MemoryPredictionRepository:
    def __init__(self) -> None:
        self.runs: dict[tuple[object, ...], PredictionRun] = {}

    async def save_if_absent(self, run: PredictionRun) -> PredictionRun:
        key = (
            run.experiment_run_id,
            run.market_id,
            run.predicted_at,
            run.agent_configuration_hash,
        )
        return self.runs.setdefault(key, run)


class MemoryUnitOfWork:
    def __init__(self, repository: MemoryPredictionRepository) -> None:
        self.predictions = repository
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


def orchestrator(repository: MemoryPredictionRepository) -> PredictionOrchestrator:
    backend = RuleBasedModelBackend()
    return PredictionOrchestrator(
        market_repository=MemoryMarketRepository(),
        unit_of_work=lambda: MemoryUnitOfWork(repository),
        reasoning_agent=ReasoningAgent(backend),
        market_agent=MarketAgent(backend),
        skeptic_agent=SkepticAgent(backend),
        consensus_agent=ConsensusAgent(backend),
        clock=FixedClock(),
    )


@pytest.mark.asyncio
async def test_orchestrator_is_transactional_traceable_and_idempotent() -> None:
    repository = MemoryPredictionRepository()
    service = orchestrator(repository)
    command = RunPrediction(
        market_id=MARKET_ID,
        predicted_at=NOW,
        context={"probability_adjustment": "0.15"},
        correlation_id="prediction-test",
        causation_id="unit-test",
    )

    first = await service.run(command)
    second = await service.run(command)

    assert first.prediction_run_id == second.prediction_run_id
    assert first.result_hash == second.result_hash
    assert len(first.agent_predictions) == 4
    assert first.correlation_id == "prediction-test"
    assert first.causation_id == "unit-test"
    assert len(repository.runs) == 1
