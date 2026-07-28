"""Deterministic initial model backends with no external I/O."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from itertools import pairwise

from predictionlab.application.agents import ModelAssessment
from predictionlab.domain.agents import (
    AgentEvidence,
    AgentPrediction,
    EvidenceDirection,
    PredictionAgentInput,
    Recommendation,
)
from predictionlab.domain.markets import MarketStatus

_ZERO = Decimal("0")
_ONE = Decimal("1")


class RuleBasedModelBackend:
    backend_name = "rule_based"
    backend_version = "1.0.0"

    async def assess(
        self,
        *,
        agent_name: str,
        agent_input: PredictionAgentInput,
    ) -> ModelAssessment:
        methods = {
            "reasoning": self._reasoning,
            "market": self._market,
            "skeptic": self._skeptic,
            "consensus": self._consensus,
        }
        try:
            method = methods[agent_name]
        except KeyError as exc:
            raise ValueError(f"unsupported rule-based agent: {agent_name}") from exc
        return method(agent_input)

    def _reasoning(self, data: PredictionAgentInput) -> ModelAssessment:
        unavailable = _basic_unavailability(data)
        if unavailable is not None:
            return unavailable
        assert data.market_probability is not None
        probabilities = _probabilities(data)
        trend = probabilities[-1] - probabilities[0] if len(probabilities) > 1 else _ZERO
        context_adjustment = _context_decimal(
            data.context,
            "probability_adjustment",
            lower=Decimal("-0.25"),
            upper=Decimal("0.25"),
        )
        adjustment = trend * Decimal("0.50") + context_adjustment
        predicted = _clamp(data.market_probability + adjustment)
        confidence = Decimal("0.30")
        evidence: list[AgentEvidence] = [
            _evidence(
                "market_anchor",
                "La estimación parte de la probabilidad visible del mercado.",
                EvidenceDirection.NEUTRAL,
                Decimal("0.40"),
            )
        ]
        if data.description:
            confidence += Decimal("0.08")
            evidence.append(
                _evidence(
                    "defined_event",
                    "El evento tiene una descripción disponible.",
                    EvidenceDirection.NEUTRAL,
                    Decimal("0.20"),
                )
            )
        if data.category:
            confidence += Decimal("0.03")
        warnings: list[str] = []
        if data.resolution_at is not None:
            hours_to_close = (
                data.resolution_at - data.predicted_at
            ).total_seconds() / 3_600
            if 0 <= hours_to_close <= 24:
                confidence -= Decimal("0.05")
                warnings.append(
                    "El cierre está próximo y deja poco margen para nueva evidencia."
                )
                evidence.append(
                    _evidence(
                        "close_proximity",
                        "El mercado está a menos de 24 horas del cierre previsto.",
                        EvidenceDirection.NEUTRAL,
                        Decimal("0.40"),
                    )
                )
        confidence += min(Decimal(len(probabilities)) * Decimal("0.03"), Decimal("0.15"))
        if context_adjustment != _ZERO:
            confidence += Decimal("0.12")
            evidence.append(
                _evidence(
                    "structured_context",
                    "Se aplicó un ajuste explícito del contexto estructurado.",
                    _direction(context_adjustment),
                    min(abs(context_adjustment) * Decimal("4"), _ONE),
                )
            )
        if trend != _ZERO:
            evidence.append(
                _evidence(
                    "historical_direction",
                    "El historial visible aporta una señal direccional débil.",
                    _direction(trend),
                    min(abs(trend) * Decimal("3"), _ONE),
                )
            )
        return ModelAssessment(
            predicted_probability=predicted,
            confidence=min(confidence, Decimal("0.75")),
            recommendation=_recommend(predicted, data.market_probability),
            rationale_summary=(
                "Estimación conservadora anclada al mercado, al contexto explícito "
                "y al historial disponible."
            ),
            evidence=tuple(evidence),
            warnings=(
                tuple([*warnings, "No se utilizó conocimiento externo ni noticias."])
                if context_adjustment == _ZERO
                else tuple(warnings)
            ),
        )

    def _market(self, data: PredictionAgentInput) -> ModelAssessment:
        unavailable = _basic_unavailability(data)
        if unavailable is not None:
            return unavailable
        assert data.market_probability is not None
        probabilities = _probabilities(data)[-12:]
        if not probabilities:
            return _abstain("No hay observaciones probabilísticas disponibles.")
        trend = probabilities[-1] - probabilities[0] if len(probabilities) > 1 else _ZERO
        changes = [
            abs(current - previous)
            for previous, current in pairwise(probabilities)
        ]
        volatility = sum(changes, _ZERO) / Decimal(len(changes)) if changes else _ZERO
        momentum = trend * Decimal("0.75") * max(_ZERO, _ONE - volatility * Decimal("3"))
        predicted = _clamp(data.market_probability + momentum)
        confidence = Decimal("0.30")
        confidence += min(Decimal(len(probabilities)) * Decimal("0.05"), Decimal("0.30"))
        if data.volume is not None:
            confidence += Decimal("0.06")
        if data.liquidity is not None:
            confidence += Decimal("0.08")
        confidence -= min(volatility, Decimal("0.20"))
        warnings: list[str] = []
        if len(probabilities) < 3:
            warnings.append("Historial corto: la tendencia es poco robusta.")
        if data.liquidity is None:
            warnings.append("El proveedor no informó liquidez.")
        return ModelAssessment(
            predicted_probability=predicted,
            confidence=_clamp(confidence),
            recommendation=_recommend(predicted, data.market_probability),
            rationale_summary=(
                "Lectura cuantitativa de tendencia y volatilidad usando sólo "
                "observaciones visibles del mercado."
            ),
            evidence=(
                _evidence(
                    "visible_trend",
                    "La dirección reciente se estimó con el historial disponible.",
                    _direction(trend),
                    min(abs(trend) * Decimal("4"), _ONE),
                ),
                _evidence(
                    "visible_volatility",
                    "La volatilidad reduce la fuerza de la señal.",
                    EvidenceDirection.NEUTRAL,
                    min(volatility * Decimal("5"), _ONE),
                ),
            ),
            warnings=tuple(warnings),
        )

    def _skeptic(self, data: PredictionAgentInput) -> ModelAssessment:
        required = _named_predictions(data.prior_predictions, {"reasoning", "market"})
        if len(required) != 2 or data.market_probability is None:
            return _abstain("Faltan salidas completas de ReasoningAgent y MarketAgent.")
        available = [item for item in required.values() if item.predicted_probability is not None]
        if len(available) != 2:
            return _abstain("Un agente previo se abstuvo.")
        first, second = available
        assert first.predicted_probability is not None
        assert second.predicted_probability is not None
        disagreement = abs(first.predicted_probability - second.predicted_probability)
        peer_center = (first.predicted_probability + second.predicted_probability) / Decimal("2")
        predicted = data.market_probability * Decimal("0.50") + peer_center * Decimal("0.50")
        confidence = min(first.confidence, second.confidence) * Decimal("0.80")
        confidence = _clamp(confidence - disagreement * Decimal("0.60"))
        warnings: list[str] = []
        if disagreement >= Decimal("0.15"):
            warnings.append("Los agentes previos muestran un desacuerdo relevante.")
        if data.liquidity is None:
            warnings.append("No hay liquidez informada para validar la señal.")
        peer_edges = [
            abs(item.predicted_probability - data.market_probability)
            for item in available
            if item.predicted_probability is not None
        ]
        if max(peer_edges, default=_ZERO) > Decimal("0.20"):
            warnings.append("Se moderó un edge aparente superior a 20 puntos.")
        return ModelAssessment(
            predicted_probability=predicted,
            confidence=confidence,
            recommendation=_recommend(predicted, data.market_probability),
            rationale_summary=(
                "Revisión adversarial que modera señales grandes y penaliza "
                "desacuerdo o datos incompletos."
            ),
            evidence=(
                _evidence(
                    "peer_disagreement",
                    "Se compararon las dos estimaciones independientes.",
                    EvidenceDirection.NEUTRAL,
                    disagreement,
                ),
                _evidence(
                    "market_reanchor",
                    "La estimación se reancló parcialmente al mercado.",
                    EvidenceDirection.NEUTRAL,
                    Decimal("0.60"),
                ),
            ),
            warnings=tuple(warnings),
            disagreement_score=disagreement,
        )

    def _consensus(self, data: PredictionAgentInput) -> ModelAssessment:
        required = _named_predictions(
            data.prior_predictions,
            {"reasoning", "market", "skeptic"},
        )
        if data.status is not MarketStatus.OPEN:
            return _abstain("El mercado no está abierto.")
        if data.market_probability is None:
            return _abstain("Falta la probabilidad visible del mercado.")
        if not data.observations:
            return _abstain("No hay observaciones disponibles.")
        maximum_age = _config_int(
            data,
            "maximum_observation_age_seconds",
            172_800,
        )
        age_seconds = (data.predicted_at - data.observations[-1].observed_at).total_seconds()
        if age_seconds > maximum_age:
            return _abstain("La observación más reciente es demasiado antigua.")
        available = [
            item
            for item in required.values()
            if item.predicted_probability is not None
            and item.recommendation is not Recommendation.ABSTAIN
        ]
        if len(available) < 2:
            return _abstain("No hay suficientes estimaciones independientes.")
        probabilities = [
            item.predicted_probability
            for item in available
            if item.predicted_probability is not None
        ]
        disagreement = max(probabilities) - min(probabilities)
        max_disagreement = _config_decimal(
            data,
            "maximum_disagreement",
            Decimal("0.30"),
        )
        if disagreement > max_disagreement:
            return _abstain(
                "El desacuerdo entre agentes supera el umbral configurado.",
                disagreement=disagreement,
            )
        base_weights = {
            "reasoning": _config_decimal(data, "reasoning_weight", Decimal("0.25")),
            "market": _config_decimal(data, "market_weight", Decimal("0.35")),
            "skeptic": _config_decimal(data, "skeptic_weight", Decimal("0.40")),
        }
        effective = {
            item.agent_name: base_weights[item.agent_name]
            * max(item.confidence, Decimal("0.05"))
            for item in available
        }
        total_weight = sum(effective.values(), _ZERO)
        normalized = {
            name: weight / total_weight for name, weight in effective.items()
        }
        predicted = sum(
            (
                item.predicted_probability * normalized[item.agent_name]
                for item in available
                if item.predicted_probability is not None
            ),
            _ZERO,
        )
        weighted_confidence = sum(
            (item.confidence * normalized[item.agent_name] for item in available),
            _ZERO,
        )
        confidence = _clamp(weighted_confidence * (_ONE - disagreement))
        minimum_confidence = _config_decimal(
            data,
            "minimum_confidence",
            Decimal("0.40"),
        )
        weak_edge = _config_decimal(data, "weak_edge", Decimal("0.03"))
        edge = predicted - data.market_probability
        warnings = tuple(
            dict.fromkeys(
                warning
                for item in available
                for warning in item.warnings
            )
        )
        if confidence < minimum_confidence:
            return _abstain(
                "La confianza del consenso no alcanza el umbral configurado.",
                confidence=confidence,
                disagreement=disagreement,
                weights=normalized,
                warnings=warnings,
            )
        if abs(edge) < weak_edge:
            return _abstain(
                "La diferencia frente al mercado es demasiado pequeña.",
                confidence=confidence,
                disagreement=disagreement,
                weights=normalized,
                warnings=warnings,
            )
        extreme_floor = _config_decimal(data, "extreme_probability_floor", Decimal("0.02"))
        extreme_ceiling = _config_decimal(
            data,
            "extreme_probability_ceiling",
            Decimal("0.98"),
        )
        minimum_extreme_observations = _config_int(
            data,
            "minimum_extreme_observations",
            3,
        )
        if (
            predicted <= extreme_floor or predicted >= extreme_ceiling
        ) and len(_probabilities(data)) < minimum_extreme_observations:
            return _abstain(
                "Una probabilidad extrema requiere más observaciones.",
                confidence=confidence,
                disagreement=disagreement,
                weights=normalized,
                warnings=warnings,
            )
        return ModelAssessment(
            predicted_probability=predicted,
            confidence=confidence,
            recommendation=Recommendation.YES if edge > 0 else Recommendation.NO,
            rationale_summary=(
                "Consenso ponderado por rol y confianza, con penalización por "
                "desacuerdo entre agentes."
            ),
            evidence=(
                _evidence(
                    "weighted_consensus",
                    "Los agentes se ponderaron por rol y confianza declarada.",
                    _direction(edge),
                    min(abs(edge) * Decimal("4"), _ONE),
                ),
                _evidence(
                    "disagreement_penalty",
                    "El desacuerdo redujo la confianza final.",
                    EvidenceDirection.NEUTRAL,
                    disagreement,
                ),
            ),
            warnings=warnings,
            disagreement_score=disagreement,
            agent_weights=normalized,
        )


class MockModelBackend:
    backend_name = "mock"
    backend_version = "1.0.0"

    def __init__(self, assessments: Mapping[str, ModelAssessment]) -> None:
        self._assessments = dict(assessments)
        self.calls: list[tuple[str, str]] = []

    async def assess(
        self,
        *,
        agent_name: str,
        agent_input: PredictionAgentInput,
    ) -> ModelAssessment:
        self.calls.append((agent_name, agent_input.input_hash))
        try:
            return self._assessments[agent_name]
        except KeyError as exc:
            raise ValueError(f"no mock assessment for {agent_name}") from exc


def _basic_unavailability(data: PredictionAgentInput) -> ModelAssessment | None:
    if data.status is not MarketStatus.OPEN:
        return _abstain("El mercado no está abierto.")
    if data.market_probability is None:
        return _abstain("Falta la probabilidad visible del mercado.")
    return None


def _abstain(
    reason: str,
    *,
    confidence: Decimal = _ZERO,
    disagreement: Decimal | None = None,
    weights: dict[str, Decimal] | None = None,
    warnings: tuple[str, ...] = (),
) -> ModelAssessment:
    return ModelAssessment(
        predicted_probability=None,
        confidence=confidence,
        recommendation=Recommendation.ABSTAIN,
        rationale_summary=reason,
        evidence=(),
        warnings=warnings,
        disagreement_score=disagreement,
        agent_weights=weights or {},
    )


def _probabilities(data: PredictionAgentInput) -> list[Decimal]:
    return [
        observation.probability
        for observation in data.observations
        if observation.probability is not None
    ]


def _named_predictions(
    predictions: tuple[AgentPrediction, ...],
    names: set[str],
) -> dict[str, AgentPrediction]:
    return {item.agent_name: item for item in predictions if item.agent_name in names}


def _evidence(
    code: str,
    summary: str,
    direction: EvidenceDirection,
    strength: Decimal,
) -> AgentEvidence:
    return AgentEvidence(
        code=code,
        summary=summary,
        direction=direction,
        strength=_clamp(strength),
    )


def _direction(value: Decimal) -> EvidenceDirection:
    if value > 0:
        return EvidenceDirection.YES
    if value < 0:
        return EvidenceDirection.NO
    return EvidenceDirection.NEUTRAL


def _recommend(probability: Decimal, market_probability: Decimal) -> Recommendation:
    return Recommendation.YES if probability >= market_probability else Recommendation.NO


def _clamp(value: Decimal) -> Decimal:
    return min(max(value, _ZERO), _ONE)


def _context_decimal(
    values: Mapping[str, object],
    key: str,
    *,
    lower: Decimal,
    upper: Decimal,
) -> Decimal:
    raw = values.get(key)
    if raw is None or isinstance(raw, bool):
        return _ZERO
    try:
        value = Decimal(str(raw))
    except Exception:
        return _ZERO
    return min(max(value, lower), upper) if value.is_finite() else _ZERO


def _config_decimal(
    data: PredictionAgentInput,
    key: str,
    default: Decimal,
) -> Decimal:
    raw = data.model_configuration.get(key)
    if raw is None or isinstance(raw, bool):
        return default
    try:
        value = Decimal(str(raw))
    except Exception:
        return default
    return value if value.is_finite() else default


def _config_int(data: PredictionAgentInput, key: str, default: int) -> int:
    raw = data.model_configuration.get(key)
    if raw is None or isinstance(raw, bool):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
