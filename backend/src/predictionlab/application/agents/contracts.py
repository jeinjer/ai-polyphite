"""Application ports for prediction agents and their model backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from predictionlab.domain.agents import (
    AgentEvidence,
    AgentPrediction,
    PredictionAgentInput,
    Recommendation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelAssessment:
    predicted_probability: Decimal | None
    confidence: Decimal
    recommendation: Recommendation
    rationale_summary: str
    evidence: tuple[AgentEvidence, ...]
    warnings: tuple[str, ...] = ()
    disagreement_score: Decimal | None = None
    agent_weights: dict[str, Decimal] = field(default_factory=dict)


class ModelBackend(Protocol):
    backend_name: str
    backend_version: str

    async def assess(
        self,
        *,
        agent_name: str,
        agent_input: PredictionAgentInput,
    ) -> ModelAssessment: ...


class PredictionAgent(Protocol):
    name: str
    version: str

    async def predict(self, agent_input: PredictionAgentInput) -> AgentPrediction: ...
