from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from predictionlab.domain.agents import (
    AgentInvariantError,
    AgentObservation,
    PredictionAgentInput,
)
from predictionlab.domain.markets import MarketStatus

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def agent_input() -> PredictionAgentInput:
    return PredictionAgentInput(
        market_id=uuid4(),
        title="¿Ocurrirá el evento?",
        description="Definición estructurada.",
        category="testing",
        status=MarketStatus.OPEN,
        predicted_at=NOW,
        resolution_at=NOW + timedelta(days=3),
        market_probability=Decimal("0.55"),
        observations=(
            AgentObservation(
                observed_at=NOW - timedelta(hours=2),
                probability=Decimal("0.50"),
                volume=Decimal("10"),
                liquidity=Decimal("5"),
            ),
            AgentObservation(
                observed_at=NOW,
                probability=Decimal("0.55"),
                volume=Decimal("12"),
                liquidity=Decimal("6"),
            ),
        ),
        volume=Decimal("12"),
        liquidity=Decimal("6"),
        context={},
        experiment_run_id=None,
        random_seed=7,
        model_configuration={},
    )


def test_agent_input_hash_is_deterministic_and_excludes_experiment_linkage() -> None:
    original = agent_input()
    linked = replace(original, experiment_run_id=uuid4())

    assert original.input_hash == linked.input_hash
    assert len(original.input_hash) == 64


def test_agent_input_rejects_future_observations() -> None:
    with pytest.raises(AgentInvariantError, match="future observations"):
        replace(
            agent_input(),
            observations=(
                AgentObservation(
                    observed_at=NOW + timedelta(seconds=1),
                    probability=Decimal("0.50"),
                    volume=None,
                    liquidity=None,
                ),
            ),
        )


def test_agent_observation_rejects_invalid_probability() -> None:
    with pytest.raises(AgentInvariantError, match="between 0 and 1"):
        AgentObservation(
            observed_at=NOW,
            probability=Decimal("1.01"),
            volume=None,
            liquidity=None,
        )
