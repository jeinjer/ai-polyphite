"""Inputs for commercial evaluation of a persisted prediction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from predictionlab.domain.predictions import EstimatedOutcome, PredictionRunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCommercialOpportunity:
    prediction_run_id: UUID
    portfolio_id: UUID | None
    evaluated_at: datetime
    prediction_status: PredictionRunStatus
    estimated_outcome: EstimatedOutcome | None
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    confidence: Decimal
    market_is_open: bool
    data_age: timedelta | None
    liquidity: Decimal | None
    proposed_stake: Decimal
    portfolio_is_active: bool
    portfolio_has_open_position: bool
    campaign_is_active: bool = True
    entry_reasons: tuple[str, ...] = ()
    risk_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        object.__setattr__(
            self,
            "evaluated_at",
            self.evaluated_at.astimezone(UTC),
        )
        if self.data_age is not None and self.data_age < timedelta(0):
            raise ValueError("data_age cannot be negative")
        if self.proposed_stake < 0:
            raise ValueError("proposed_stake cannot be negative")
