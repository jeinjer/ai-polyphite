"""Pure post-resolution scoring, intentionally separate from prediction generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ProbabilityBaseline(Protocol):
    name: str

    def probability(self, market_probability: Decimal) -> Decimal: ...


@dataclass(frozen=True, slots=True)
class MarketBaseline:
    name: str = "market"

    def probability(self, market_probability: Decimal) -> Decimal:
        return market_probability


@dataclass(frozen=True, slots=True)
class ConstantBaseline:
    value: Decimal = Decimal("0.50")
    name: str = "constant_0_50"

    def probability(self, market_probability: Decimal) -> Decimal:
        del market_probability
        return self.value


@dataclass(frozen=True, slots=True)
class ProbabilityScore:
    brier_score: Decimal
    log_loss: Decimal
    absolute_error: Decimal
    directionally_correct: bool


def score_probability(
    probability: Decimal,
    outcome: Decimal,
) -> ProbabilityScore:
    _unit_interval(probability, "probability")
    _unit_interval(outcome, "outcome")
    if outcome not in {Decimal("0"), Decimal("1")}:
        raise ValueError("outcome must be binary")
    error = probability - outcome
    clipped = min(max(float(probability), 1e-15), 1 - 1e-15)
    observed = float(outcome)
    loss = -(observed * math.log(clipped) + (1 - observed) * math.log(1 - clipped))
    return ProbabilityScore(
        brier_score=error * error,
        log_loss=Decimal(str(loss)),
        absolute_error=abs(error),
        directionally_correct=(probability >= Decimal("0.5")) == (outcome == Decimal("1")),
    )


def _unit_interval(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field_name} must be a finite Decimal")
    if not Decimal("0") <= value <= Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1")
