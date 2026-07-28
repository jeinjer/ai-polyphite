"""Framework-free contracts shared by deterministic prediction agents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.markets import MarketStatus

type JsonScalar = bool | int | float | str | None
type StructuredValues = Mapping[str, JsonScalar]

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class AgentInvariantError(ValueError):
    pass


class Recommendation(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class EvidenceDirection(StrEnum):
    YES = "yes"
    NO = "no"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentEvidence:
    code: str
    summary: str
    direction: EvidenceDirection
    strength: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "code", 100))
        object.__setattr__(self, "summary", _text(self.summary, "summary", 500))
        _probability(self.strength, "strength")


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentObservation:
    observed_at: datetime
    probability: Decimal | None
    volume: Decimal | None
    liquidity: Decimal | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        if self.probability is not None:
            _probability(self.probability, "probability")
        for field_name in ("volume", "liquidity"):
            value = getattr(self, field_name)
            if value is not None:
                _non_negative(value, field_name)
        if all(
            value is None
            for value in (self.probability, self.volume, self.liquidity)
        ):
            raise AgentInvariantError("an observation must contain at least one value")


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentPrediction:
    agent_name: str
    agent_version: str
    predicted_probability: Decimal | None
    confidence: Decimal
    recommendation: Recommendation
    rationale_summary: str
    evidence: tuple[AgentEvidence, ...]
    warnings: tuple[str, ...]
    input_hash: str
    output_hash: str
    duration_ms: Decimal
    disagreement_score: Decimal | None = None
    agent_weights: Mapping[str, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_name", _text(self.agent_name, "agent_name", 100))
        object.__setattr__(
            self,
            "agent_version",
            _text(self.agent_version, "agent_version", 50),
        )
        if self.predicted_probability is not None:
            _probability(self.predicted_probability, "predicted_probability")
        _probability(self.confidence, "confidence")
        if self.recommendation is Recommendation.ABSTAIN:
            if self.predicted_probability is not None:
                raise AgentInvariantError(
                    "abstaining agents cannot publish a predicted probability"
                )
        elif self.predicted_probability is None:
            raise AgentInvariantError("non-abstaining agents require a probability")
        object.__setattr__(
            self,
            "rationale_summary",
            _text(self.rationale_summary, "rationale_summary", 2_000),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(_text(item, "warning", 500) for item in self.warnings),
        )
        for field_name in ("input_hash", "output_hash"):
            if not _SHA256_PATTERN.fullmatch(getattr(self, field_name)):
                raise AgentInvariantError(f"{field_name} must be a SHA-256 digest")
        _non_negative(self.duration_ms, "duration_ms")
        if self.disagreement_score is not None:
            _probability(self.disagreement_score, "disagreement_score")
        for agent_name, weight in self.agent_weights.items():
            _text(agent_name, "agent weight name", 100)
            _probability(weight, "agent weight")
        object.__setattr__(
            self,
            "agent_weights",
            MappingProxyType(dict(self.agent_weights)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PredictionAgentInput:
    market_id: UUID
    title: str
    description: str | None
    category: str | None
    status: MarketStatus
    predicted_at: datetime
    resolution_at: datetime | None
    market_probability: Decimal | None
    observations: tuple[AgentObservation, ...]
    volume: Decimal | None
    liquidity: Decimal | None
    context: StructuredValues
    experiment_run_id: UUID | None
    random_seed: int
    model_configuration: StructuredValues
    prior_predictions: tuple[AgentPrediction, ...] = ()

    def __post_init__(self) -> None:
        if self.market_id.int == 0:
            raise AgentInvariantError("market_id must be non-zero")
        object.__setattr__(self, "title", _text(self.title, "title", 1_000))
        if self.description is not None:
            object.__setattr__(
                self,
                "description",
                _text(self.description, "description", 20_000),
            )
        if self.category is not None:
            object.__setattr__(
                self,
                "category",
                _text(self.category, "category", 200),
            )
        predicted_at = _utc(self.predicted_at, "predicted_at")
        object.__setattr__(self, "predicted_at", predicted_at)
        if self.resolution_at is not None:
            object.__setattr__(
                self,
                "resolution_at",
                _utc(self.resolution_at, "resolution_at"),
            )
        if self.market_probability is not None:
            _probability(self.market_probability, "market_probability")
        for field_name in ("volume", "liquidity"):
            value = getattr(self, field_name)
            if value is not None:
                _non_negative(value, field_name)
        ordered = tuple(sorted(self.observations, key=lambda item: item.observed_at))
        if ordered != self.observations:
            raise AgentInvariantError("observations must be ordered by observed_at")
        if any(item.observed_at > predicted_at for item in ordered):
            raise AgentInvariantError("future observations are forbidden")
        if self.random_seed < 0:
            raise AgentInvariantError("random_seed cannot be negative")
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))
        object.__setattr__(
            self,
            "model_configuration",
            MappingProxyType(dict(self.model_configuration)),
        )

    @property
    def input_hash(self) -> str:
        return canonical_sha256(
            {
                "market_id": self.market_id,
                "title": self.title,
                "description": self.description,
                "category": self.category,
                "status": self.status,
                "predicted_at": self.predicted_at,
                "resolution_at": self.resolution_at,
                "market_probability": self.market_probability,
                "observations": self.observations,
                "volume": self.volume,
                "liquidity": self.liquidity,
                "context": self.context,
                "random_seed": self.random_seed,
                "model_configuration": self.model_configuration,
                "prior_outputs": tuple(item.output_hash for item in self.prior_predictions),
            }
        )


def _text(value: str, field_name: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentInvariantError(f"{field_name} cannot be blank")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise AgentInvariantError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AgentInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _probability(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if not Decimal("0") <= value <= Decimal("1"):
        raise AgentInvariantError(f"{field_name} must be between 0 and 1")


def _non_negative(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if value < 0:
        raise AgentInvariantError(f"{field_name} cannot be negative")


def _decimal(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise AgentInvariantError(f"{field_name} must be a finite Decimal")
