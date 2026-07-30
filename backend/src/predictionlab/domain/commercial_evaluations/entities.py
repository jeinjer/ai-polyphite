"""Framework-free commercial evaluation for simulated research."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from predictionlab.domain.predictions import EstimatedOutcome

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CommercialEvaluationInvariantError(ValueError):
    pass


class PotentialSide(StrEnum):
    BUY_YES = "buy_yes"
    BUY_NO = "buy_no"
    NONE = "none"


class CommercialLabel(StrEnum):
    ACTIONABLE = "actionable"
    NOT_ACTIONABLE = "not_actionable"
    NOT_EVALUABLE = "not_evaluable"


class DataFreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True, kw_only=True)
class CommercialEvaluation:
    evaluation_id: UUID
    prediction_run_id: UUID
    portfolio_id: UUID | None
    campaign_id: str
    evaluated_at: datetime
    estimated_outcome: EstimatedOutcome | None
    potential_side: PotentialSide
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    gross_edge: Decimal | None
    estimated_fees: Decimal
    estimated_slippage: Decimal
    estimated_other_costs: Decimal
    net_edge: Decimal | None
    confidence: Decimal
    commercial_label: CommercialLabel
    is_actionable: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    configuration_hash: str
    result_hash: str
    created_at: datetime
    portfolio_has_open_position: bool
    data_freshness_status: DataFreshnessStatus

    def __post_init__(self) -> None:
        _uuid(self.evaluation_id, "evaluation_id")
        _uuid(self.prediction_run_id, "prediction_run_id")
        if self.portfolio_id is not None:
            _uuid(self.portfolio_id, "portfolio_id")
        _text(self.campaign_id, "campaign_id", 160)
        object.__setattr__(
            self,
            "evaluated_at",
            _utc(self.evaluated_at, "evaluated_at"),
        )
        object.__setattr__(
            self,
            "created_at",
            _utc(self.created_at, "created_at"),
        )
        for field_name in ("market_probability", "consensus_probability"):
            value = getattr(self, field_name)
            if value is not None:
                _probability(value, field_name)
        for field_name in (
            "estimated_fees",
            "estimated_slippage",
            "estimated_other_costs",
        ):
            _probability(getattr(self, field_name), field_name)
        for field_name in ("gross_edge", "net_edge"):
            value = getattr(self, field_name)
            if value is not None:
                _edge(value, field_name)
        _probability(self.confidence, "confidence")
        if self.is_actionable != (
            self.commercial_label is CommercialLabel.ACTIONABLE
        ):
            raise CommercialEvaluationInvariantError(
                "is_actionable must match commercial_label"
            )
        if self.commercial_label is CommercialLabel.NOT_EVALUABLE:
            if self.potential_side is not PotentialSide.NONE:
                raise CommercialEvaluationInvariantError(
                    "not evaluable assessment cannot publish a potential side"
                )
        elif self.estimated_outcome is None:
            raise CommercialEvaluationInvariantError(
                "evaluable assessment requires estimated_outcome"
            )
        if not self.reasons:
            raise CommercialEvaluationInvariantError(
                "commercial evaluation requires at least one reason"
            )
        for value in self.reasons:
            _text(value, "reason", 200)
        for value in self.warnings:
            _text(value, "warning", 500)
        for field_name in ("configuration_hash", "result_hash"):
            if not _SHA256_PATTERN.fullmatch(getattr(self, field_name)):
                raise CommercialEvaluationInvariantError(
                    f"{field_name} must be a SHA-256 digest"
                )


def _uuid(value: UUID, field_name: str) -> None:
    if not isinstance(value, UUID) or value.int == 0:
        raise CommercialEvaluationInvariantError(f"{field_name} must be non-zero")


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CommercialEvaluationInvariantError(
            f"{field_name} must be timezone-aware"
        )
    return value.astimezone(UTC)


def _text(value: str, field_name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CommercialEvaluationInvariantError(f"{field_name} cannot be blank")
    if len(value.strip()) > maximum:
        raise CommercialEvaluationInvariantError(
            f"{field_name} cannot exceed {maximum} characters"
        )


def _probability(value: Decimal, field_name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or not Decimal("0") <= value <= Decimal("1")
    ):
        raise CommercialEvaluationInvariantError(
            f"{field_name} must be between 0 and 1"
        )


def _edge(value: Decimal, field_name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or not Decimal("-1") <= value <= Decimal("1")
    ):
        raise CommercialEvaluationInvariantError(
            f"{field_name} must be between -1 and 1"
        )
