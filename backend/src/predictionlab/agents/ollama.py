"""Structured local-LLM assessments behind the provider-neutral model port."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Literal, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from predictionlab.application.agents import ModelAssessment
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    PredictionAgentInput,
    Recommendation,
)

logger = logging.getLogger(__name__)


class ModelBackendUnavailableError(RuntimeError):
    """The local model cannot currently serve a structured assessment."""


class StructuredEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=48)
    summary: str = Field(min_length=1, max_length=180)
    direction: Literal["yes", "no", "neutral"]
    strength: Decimal = Field(ge=0, le=1)


class StructuredAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    eligible: bool
    predicted_probability: Decimal | None = Field(default=None, ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    rationale_summary: str = Field(min_length=1, max_length=600)
    evidence: tuple[StructuredEvidence, ...] = Field(max_length=3)
    warnings: tuple[str, ...] = Field(default=(), max_length=3)


# Pydantic represents Decimal as ``number | string`` and defaulted fields as
# optional.  That schema is valid JSON Schema, but some llama.cpp grammar
# versions cannot compile the resulting optional-order grammar.  Keep the
# transport contract intentionally small and require every key; Pydantic still
# performs the authoritative validation after generation.
_OLLAMA_ASSESSMENT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "eligible": {"type": "boolean"},
        "predicted_probability": {
            "anyOf": [
                {"type": "number", "minimum": 0, "maximum": 1},
                {"type": "null"},
            ]
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale_summary": {"type": "string", "maxLength": 600},
        "evidence": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "maxLength": 48},
                    "summary": {"type": "string", "maxLength": 180},
                    "direction": {"enum": ["yes", "no", "neutral"]},
                    "strength": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["code", "summary", "direction", "strength"],
                "additionalProperties": False,
            },
        },
        "warnings": {
            "type": "array",
            "maxItems": 3,
            "items": {"type": "string", "maxLength": 180},
        },
    },
    "required": [
        "eligible",
        "predicted_probability",
        "confidence",
        "rationale_summary",
        "evidence",
        "warnings",
    ],
    "additionalProperties": False,
}


class OllamaModelBackend:
    """Use Ollama only for semantic reasoning and adversarial review."""

    backend_name = "ollama"
    backend_version = "1.0.0"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        reasoning_temperature: Decimal,
        skeptic_temperature: Decimal,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = httpx.Timeout(timeout_seconds)
        self._reasoning_temperature = reasoning_temperature
        self._skeptic_temperature = skeptic_temperature
        self._client_factory = client_factory or httpx.AsyncClient

    async def assess(
        self,
        *,
        agent_name: str,
        agent_input: PredictionAgentInput,
    ) -> ModelAssessment:
        if agent_name not in {"reasoning", "skeptic"}:
            raise ValueError(f"Ollama backend does not implement {agent_name} agent")
        prompt = (
            _reasoning_prompt(agent_input)
            if agent_name == "reasoning"
            else _skeptic_prompt(agent_input)
        )
        temperature = (
            self._reasoning_temperature
            if agent_name == "reasoning"
            else self._skeptic_temperature
        )
        structured = await self._chat(prompt, temperature=temperature)
        if not structured.eligible:
            return ModelAssessment(
                predicted_probability=None,
                confidence=structured.confidence,
                recommendation=Recommendation.ABSTAIN,
                rationale_summary=structured.rationale_summary,
                evidence=_evidence(structured.evidence),
                warnings=structured.warnings,
            )
        if structured.predicted_probability is None:
            raise ModelBackendUnavailableError(
                "Ollama omitted probability for an eligible market."
            )
        probability = structured.predicted_probability
        return ModelAssessment(
            predicted_probability=probability,
            confidence=structured.confidence,
            recommendation=(
                Recommendation.YES if probability >= Decimal("0.5") else Recommendation.NO
            ),
            rationale_summary=structured.rationale_summary,
            evidence=_evidence(structured.evidence),
            warnings=structured.warnings,
        )

    async def _chat(
        self,
        prompt: str,
        *,
        temperature: Decimal,
    ) -> StructuredAssessment:
        payload = {
            "model": self._model,
            "stream": False,
            "think": False,
            "format": _OLLAMA_ASSESSMENT_SCHEMA,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sos un analista de mercados de prediccion. Responde solo con el "
                        "JSON solicitado. No inventes noticias ni hechos externos. Expresa "
                        "probabilidades calibradas, evidencia breve y dudas explicitas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "options": {
                "temperature": float(temperature),
                "num_predict": 384,
            },
            "keep_alive": "15m",
        }
        try:
            async with self._client_factory() as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                envelope = cast(dict[str, object], response.json())
                message = cast(dict[str, object], envelope["message"])
                content = message["content"]
                if not isinstance(content, str):
                    raise TypeError("Ollama message content is not text")
                return StructuredAssessment.model_validate_json(content)
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValidationError,
        ) as exc:
            logger.warning(
                "ollama_structured_assessment_failed",
                extra={
                    "model": self._model,
                    "safe_error_type": type(exc).__name__,
                },
            )
            raise ModelBackendUnavailableError(
                "Local semantic model is unavailable or returned an invalid contract."
            ) from exc


def _reasoning_prompt(data: PredictionAgentInput) -> str:
    return _prompt(
        """
TAREA: califica el mercado y, solo si es util, estima P(YES).

Rechazalo con eligible=false si es bait, trivial, circular, personal/no verificable,
ambiguo, depende de informacion privada, no tiene criterio objetivo de resolucion o
no permite una investigacion reproducible. Una pregunta puede ser real y aun asi no
ser apta. Si es apta, usa solo el contrato y los datos provistos; el precio del mercado
es una referencia, no una verdad.

Se conciso: rationale_summary debe tener como maximo dos frases, usa de cero a tres
evidencias breves y no repitas el mismo aviso.
""",
        data,
        include_prior=False,
    )


def _skeptic_prompt(data: PredictionAgentInput) -> str:
    return _prompt(
        """
TAREA: actua como revisor adversarial. Examina las estimaciones independientes,
detecta doble conteo, supuestos no respaldados, ambiguedad y exceso de confianza.
Publica tu propia P(YES), no una instruccion de compra. Rechaza con eligible=false
si el contrato no es evaluable o los agentes previos no aportan una base suficiente.

Se conciso: rationale_summary debe tener como maximo dos frases, usa de cero a tres
evidencias breves y no repitas el mismo aviso.
""",
        data,
        include_prior=True,
    )


def _prompt(
    instruction: str,
    data: PredictionAgentInput,
    *,
    include_prior: bool,
) -> str:
    horizon = (
        (data.resolution_at - data.predicted_at).total_seconds()
        if data.resolution_at is not None
        else None
    )
    values: dict[str, object] = {
        "title": data.title,
        "description": data.description[:4_000] if data.description else None,
        "category": data.category,
        "status": data.status.value,
        "predicted_at": data.predicted_at.isoformat(),
        "resolution_at": (
            data.resolution_at.isoformat() if data.resolution_at is not None else None
        ),
        "horizon_seconds": horizon,
        "market_probability": (
            str(data.market_probability) if data.market_probability is not None else None
        ),
        "recent_observations": [
            {
                "observed_at": item.observed_at.isoformat(),
                "probability": str(item.probability) if item.probability is not None else None,
                "volume": str(item.volume) if item.volume is not None else None,
                "liquidity": str(item.liquidity) if item.liquidity is not None else None,
            }
            for item in data.observations[-12:]
        ],
    }
    if include_prior:
        values["independent_assessments"] = [
            {
                "agent": item.agent_name,
                "probability": (
                    str(item.predicted_probability)
                    if item.predicted_probability is not None
                    else None
                ),
                "confidence": str(item.confidence),
                "recommendation": item.recommendation.value,
                "summary": item.rationale_summary,
                "evidence_codes": [evidence.code for evidence in item.evidence],
                "warnings": list(item.warnings),
            }
            for item in data.prior_predictions
        ]
    return (
        instruction.strip()
        + "\n\nDATOS:\n"
        + json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        + "\n\nDevuelve todos los campos del contrato JSON, incluso listas vacias y "
        "predicted_probability=null cuando eligible=false."
    )


def _evidence(values: tuple[StructuredEvidence, ...]) -> tuple[AgentEvidence, ...]:
    return tuple(
        AgentEvidence(
            code=value.code,
            summary=value.summary,
            direction=EvidenceDirection(value.direction),
            strength=value.strength,
        )
        for value in values
    )
