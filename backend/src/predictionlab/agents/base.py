"""Observable agent wrapper shared by all initial implementations."""

from __future__ import annotations

import logging
from decimal import Decimal
from time import perf_counter

from predictionlab.application.agents import ModelBackend
from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.agents import AgentPrediction, PredictionAgentInput

logger = logging.getLogger(__name__)


class BackendPredictionAgent:
    name: str
    version: str

    def __init__(self, backend: ModelBackend) -> None:
        self._backend = backend

    async def predict(self, agent_input: PredictionAgentInput) -> AgentPrediction:
        started = perf_counter()
        input_hash = agent_input.input_hash
        logger.info(
            "prediction_agent_started",
            extra={
                "agent_name": self.name,
                "agent_version": self.version,
                "market_id": str(agent_input.market_id),
                "predicted_at": agent_input.predicted_at.isoformat(),
                "input_hash": input_hash,
            },
        )
        try:
            assessment = await self._backend.assess(
                agent_name=self.name,
                agent_input=agent_input,
            )
            output_hash = canonical_sha256(
                {
                    "agent_name": self.name,
                    "agent_version": self.version,
                    "backend_name": self._backend.backend_name,
                    "backend_version": self._backend.backend_version,
                    "predicted_probability": assessment.predicted_probability,
                    "confidence": assessment.confidence,
                    "recommendation": assessment.recommendation,
                    "rationale_summary": assessment.rationale_summary,
                    "evidence": assessment.evidence,
                    "warnings": assessment.warnings,
                    "disagreement_score": assessment.disagreement_score,
                    "agent_weights": assessment.agent_weights,
                }
            )
            duration_ms = _milliseconds(started)
            result = AgentPrediction(
                agent_name=self.name,
                agent_version=self.version,
                predicted_probability=assessment.predicted_probability,
                confidence=assessment.confidence,
                recommendation=assessment.recommendation,
                rationale_summary=assessment.rationale_summary,
                evidence=assessment.evidence,
                warnings=assessment.warnings,
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=duration_ms,
                disagreement_score=assessment.disagreement_score,
                agent_weights=assessment.agent_weights,
            )
            logger.info(
                "prediction_agent_finished",
                extra={
                    "agent_name": self.name,
                    "agent_version": self.version,
                    "market_id": str(agent_input.market_id),
                    "recommendation": result.recommendation.value,
                    "output_hash": output_hash,
                    "duration_ms": str(duration_ms),
                },
            )
            return result
        except Exception:
            logger.exception(
                "prediction_agent_failed",
                extra={
                    "agent_name": self.name,
                    "agent_version": self.version,
                    "market_id": str(agent_input.market_id),
                    "input_hash": input_hash,
                    "duration_ms": str(_milliseconds(started)),
                },
            )
            raise


def _milliseconds(started: float) -> Decimal:
    return Decimal(str(round((perf_counter() - started) * 1_000, 3)))
