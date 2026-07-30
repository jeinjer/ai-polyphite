from __future__ import annotations

from dataclasses import replace
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
from predictionlab.domain.agents import (
    AgentObservation,
    PredictionAgentInput,
    Recommendation,
)
from predictionlab.domain.markets import MarketStatus

NOW = datetime(2026, 1, 5, tzinfo=UTC)
MARKET_ID = UUID("00000000-0000-4000-8000-000000000505")


def input_for(
    *,
    status: MarketStatus = MarketStatus.OPEN,
    context: dict[str, str] | None = None,
) -> PredictionAgentInput:
    return PredictionAgentInput(
        market_id=MARKET_ID,
        title="¿Se cumplirá el evento estructurado?",
        description="Evento binario sintético.",
        category="testing",
        status=status,
        predicted_at=NOW,
        resolution_at=NOW + timedelta(days=3),
        market_probability=Decimal("0.55"),
        observations=tuple(
            AgentObservation(
                observed_at=NOW - timedelta(hours=3 - index),
                probability=probability,
                volume=Decimal("100") + index,
                liquidity=Decimal("50") + index,
            )
            for index, probability in enumerate(
                (
                    Decimal("0.40"),
                    Decimal("0.45"),
                    Decimal("0.50"),
                    Decimal("0.55"),
                )
            )
        ),
        volume=Decimal("103"),
        liquidity=Decimal("53"),
        context=context or {},
        experiment_run_id=None,
        random_seed=9,
        model_configuration={
            "minimum_confidence": "0.20",
            "maximum_disagreement": "0.30",
            "weak_edge": "0.03",
        },
    )


async def pipeline(data: PredictionAgentInput):
    backend = RuleBasedModelBackend()
    outputs = []
    for agent in (
        ReasoningAgent(backend),
        MarketAgent(backend),
        SkepticAgent(backend),
        ConsensusAgent(backend),
    ):
        outputs.append(await agent.predict(replace(data, prior_predictions=tuple(outputs))))
    return tuple(outputs)


@pytest.mark.asyncio
async def test_four_agents_are_deterministic_and_consensus_is_traceable() -> None:
    first = await pipeline(input_for())
    second = await pipeline(input_for())

    assert [item.output_hash for item in first] == [item.output_hash for item in second]
    assert [item.agent_name for item in first] == [
        "reasoning",
        "market",
        "skeptic",
        "consensus",
    ]
    consensus = first[-1]
    assert consensus.recommendation in {Recommendation.YES, Recommendation.NO}
    assert consensus.predicted_probability is not None
    assert set(consensus.agent_weights) == {"reasoning", "market", "skeptic"}
    assert sum(consensus.agent_weights.values()) == pytest.approx(Decimal("1"))


@pytest.mark.asyncio
async def test_closed_market_causes_explicit_abstention() -> None:
    outputs = await pipeline(input_for(status=MarketStatus.CLOSED))

    assert outputs[-1].recommendation is Recommendation.ABSTAIN
    assert outputs[-1].predicted_probability is None
    assert "no está abierto" in outputs[-1].rationale_summary


@pytest.mark.asyncio
async def test_consensus_abstains_when_disagreement_threshold_is_exceeded() -> None:
    data = input_for(context={"probability_adjustment": "0.25"})
    data = replace(
        data,
        model_configuration={
            **data.model_configuration,
            "maximum_disagreement": "0.01",
        },
    )

    outputs = await pipeline(data)

    assert outputs[-1].recommendation is Recommendation.ABSTAIN
    assert "desacuerdo" in outputs[-1].rationale_summary


@pytest.mark.asyncio
async def test_consensus_v2_keeps_probability_when_edge_is_zero() -> None:
    data = input_for()
    data = replace(
        data,
        observations=tuple(
            replace(item, probability=Decimal("0.55")) for item in data.observations
        ),
    )

    outputs = await pipeline(data)
    consensus = outputs[-1]

    assert consensus.predicted_probability == Decimal("0.55")
    assert consensus.recommendation is Recommendation.YES
    assert any("umbral comercial" in warning for warning in consensus.warnings)
