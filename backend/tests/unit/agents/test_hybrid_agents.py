from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
import pytest

from predictionlab.agents import HybridModelBackend, ReasoningAgent, RuleBasedModelBackend
from predictionlab.agents.ollama import OllamaModelBackend
from predictionlab.domain.agents import AgentObservation, PredictionAgentInput, Recommendation
from predictionlab.domain.markets import MarketStatus

NOW = datetime(2026, 8, 12, 12, tzinfo=UTC)
MARKET_ID = UUID("00000000-0000-4000-8000-000000000777")


def _input(*, title: str = "Will the public event happen tomorrow?") -> PredictionAgentInput:
    return PredictionAgentInput(
        market_id=MARKET_ID,
        title=title,
        description="Resolves from a public source at the stated deadline.",
        category="public-events",
        status=MarketStatus.OPEN,
        predicted_at=NOW,
        resolution_at=NOW + timedelta(days=1),
        market_probability=Decimal("0.60"),
        observations=(
            AgentObservation(
                observed_at=NOW - timedelta(hours=1),
                probability=Decimal("0.58"),
                volume=Decimal("100"),
                liquidity=Decimal("50"),
            ),
        ),
        volume=Decimal("100"),
        liquidity=Decimal("50"),
        context={},
        experiment_run_id=None,
        random_seed=17,
        model_configuration={
            "minimum_resolution_horizon_seconds": 300,
            "maximum_resolution_horizon_seconds": 1_209_600,
        },
    )


def _ollama(handler) -> OllamaModelBackend:
    return OllamaModelBackend(
        base_url="http://ollama:11434",
        model="fixture-model",
        timeout_seconds=2,
        reasoning_temperature=Decimal("0.30"),
        skeptic_temperature=Decimal("0.45"),
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


@pytest.mark.asyncio
async def test_ollama_reasoning_uses_validated_structured_output() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        content = json.dumps(
            {
                "eligible": True,
                "predicted_probability": "0.72",
                "confidence": "0.64",
                "rationale_summary": "Contrato verificable y de corto plazo.",
                "evidence": [
                    {
                        "code": "objective_resolution",
                        "summary": "La resolucion usa una fuente publica.",
                        "direction": "neutral",
                        "strength": "0.8",
                    }
                ],
                "warnings": ["No se consultaron noticias externas."],
            }
        )
        return httpx.Response(
            200,
            json={"message": {"content": content}},
            request=request,
        )

    assessment = await _ollama(handler).assess(
        agent_name="reasoning",
        agent_input=_input(),
    )

    assert assessment.predicted_probability == Decimal("0.72")
    assert assessment.recommendation is Recommendation.YES
    assert captured["stream"] is False
    assert isinstance(captured["format"], dict)


@pytest.mark.asyncio
async def test_hybrid_backend_falls_back_and_opens_circuit() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, request=request)

    backend = HybridModelBackend(
        ollama=_ollama(handler),
        circuit_breaker_seconds=300,
    )
    agent = ReasoningAgent(backend)

    first = await agent.predict(_input())
    second = await agent.predict(_input())

    assert calls == 1
    assert first.predicted_probability is not None
    assert second.predicted_probability == first.predicted_probability
    assert any("baseline reproducible" in warning for warning in first.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title",
    [
        "**does 1 + 1 = 2?",
        "Will I get a job before March?",
        "Will this market resolve YES?",
    ],
)
async def test_rule_based_safety_gate_rejects_bait_personal_and_circular_markets(
    title: str,
) -> None:
    result = await ReasoningAgent(RuleBasedModelBackend()).predict(_input(title=title))

    assert result.recommendation is Recommendation.ABSTAIN
    assert result.predicted_probability is None


@pytest.mark.asyncio
async def test_rule_based_safety_gate_rejects_long_horizon() -> None:
    data = replace(_input(), resolution_at=NOW + timedelta(days=30))

    result = await ReasoningAgent(RuleBasedModelBackend()).predict(data)

    assert result.recommendation is Recommendation.ABSTAIN


@pytest.mark.asyncio
async def test_hybrid_safety_gate_rejects_bait_without_calling_ollama() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    result = await ReasoningAgent(
        HybridModelBackend(ollama=_ollama(handler))
    ).predict(_input(title="**does 1 + 1 = 2?"))

    assert result.recommendation is Recommendation.ABSTAIN
    assert calls == 0
