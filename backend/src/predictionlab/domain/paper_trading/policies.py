"""Versionable entry, sizing, risk and simulated execution policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Protocol

from predictionlab.domain.paper_trading.entities import (
    PaperTradingInvariantError,
    PositionSide,
    TradeDecisionType,
)
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus

_AMOUNT_QUANTUM = Decimal("0.00000001")
_PROBABILITY_CEILING = Decimal("0.9999999999")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdEntryConfiguration:
    minimum_absolute_edge: Decimal = Decimal("0.03")
    minimum_confidence: Decimal = Decimal("0.45")
    maximum_data_age: timedelta = timedelta(days=2)
    allowed_opportunity_levels: frozenset[OpportunityLevel] = frozenset(
        {
            OpportunityLevel.WEAK,
            OpportunityLevel.MODERATE,
            OpportunityLevel.STRONG,
        }
    )
    allow_yes: bool = True
    allow_no: bool = True
    one_position_per_market: bool = True
    minimum_stake: Decimal = Decimal("0.50")
    maximum_stake: Decimal = Decimal("10.00")

    def __post_init__(self) -> None:
        _probability(self.minimum_absolute_edge, "minimum_absolute_edge")
        _probability(self.minimum_confidence, "minimum_confidence")
        if self.maximum_data_age <= timedelta(0):
            raise PaperTradingInvariantError("maximum_data_age must be positive")
        if not self.allowed_opportunity_levels:
            raise PaperTradingInvariantError("allowed_opportunity_levels cannot be empty")
        _positive(self.minimum_stake, "minimum_stake")
        _positive(self.maximum_stake, "maximum_stake")
        if self.minimum_stake > self.maximum_stake:
            raise PaperTradingInvariantError("minimum_stake cannot exceed maximum_stake")


@dataclass(frozen=True, slots=True, kw_only=True)
class EntryContext:
    prediction_status: PredictionRunStatus
    market_is_open: bool
    market_probability: Decimal | None
    system_probability: Decimal | None
    yes_edge: Decimal | None
    confidence: Decimal
    opportunity_level: OpportunityLevel
    data_age: timedelta | None
    has_existing_position: bool
    data_complete: bool


@dataclass(frozen=True, slots=True)
class EntryAssessment:
    decision: TradeDecisionType
    side: PositionSide | None
    rejection_reasons: tuple[str, ...]
    checks: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.side is not None and self.decision in {
            TradeDecisionType.BUY_YES,
            TradeDecisionType.BUY_NO,
        }


class EntryPolicy(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def evaluate(self, context: EntryContext) -> EntryAssessment: ...


class ThresholdEntryPolicy:
    name = "threshold_entry"
    version = "1.0.0"

    def __init__(
        self,
        configuration: ThresholdEntryConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or ThresholdEntryConfiguration()

    def evaluate(self, context: EntryContext) -> EntryAssessment:
        checks: list[str] = []
        reasons: list[str] = []
        if context.prediction_status is PredictionRunStatus.ABSTAINED:
            return EntryAssessment(
                decision=TradeDecisionType.ABSTAIN,
                side=None,
                rejection_reasons=("prediction_abstained",),
                checks=("prediction_status:abstained",),
            )
        if context.prediction_status is not PredictionRunStatus.COMPLETED:
            reasons.append("prediction_unavailable")
        else:
            checks.append("prediction_status:passed")
        if not context.market_is_open:
            reasons.append("market_closed_or_resolved")
        else:
            checks.append("market_status:passed")
        if not context.data_complete:
            reasons.append("incomplete_data")
        else:
            checks.append("data_completeness:passed")
        if context.data_age is None:
            reasons.append("incomplete_data")
        elif context.data_age > self.configuration.maximum_data_age:
            reasons.append("stale_observation")
        else:
            checks.append("data_freshness:passed")
        if context.confidence < self.configuration.minimum_confidence:
            reasons.append("insufficient_confidence")
        else:
            checks.append("confidence:passed")
        if context.opportunity_level not in self.configuration.allowed_opportunity_levels:
            reasons.append("opportunity_level_not_allowed")
        else:
            checks.append("opportunity_level:passed")
        if context.yes_edge is None:
            reasons.append("incomplete_data")
            side = None
        elif abs(context.yes_edge) < self.configuration.minimum_absolute_edge:
            reasons.append("insufficient_edge")
            side = None
        elif context.yes_edge > 0:
            side = PositionSide.YES
            if not self.configuration.allow_yes:
                reasons.append("yes_side_disabled")
        else:
            side = PositionSide.NO
            if not self.configuration.allow_no:
                reasons.append("no_side_disabled")
        if (
            context.yes_edge is not None
            and abs(context.yes_edge) >= self.configuration.minimum_absolute_edge
        ):
            checks.append("edge:passed")
        if self.configuration.one_position_per_market and context.has_existing_position:
            reasons.append("incompatible_existing_position")
        else:
            checks.append("position_uniqueness:passed")
        unique_reasons = tuple(dict.fromkeys(reasons))
        if unique_reasons or side is None:
            return EntryAssessment(
                decision=TradeDecisionType.REJECTED,
                side=None,
                rejection_reasons=unique_reasons or ("incomplete_data",),
                checks=tuple(checks),
            )
        return EntryAssessment(
            decision=(
                TradeDecisionType.BUY_YES if side is PositionSide.YES else TradeDecisionType.BUY_NO
            ),
            side=side,
            rejection_reasons=(),
            checks=tuple(checks),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionSizingConfiguration:
    base_equity_fraction: Decimal = Decimal("0.01")
    minimum_stake: Decimal = Decimal("0.50")
    maximum_stake: Decimal = Decimal("10.00")
    maximum_market_fraction: Decimal = Decimal("0.02")
    maximum_category_fraction: Decimal = Decimal("0.15")
    maximum_total_exposure_fraction: Decimal = Decimal("0.50")
    disagreement_reduction: Decimal = Decimal("0.50")
    low_liquidity_reduction: Decimal = Decimal("0.50")
    stale_data_reduction: Decimal = Decimal("0.50")
    low_liquidity_threshold: Decimal = Decimal("25")
    stale_after: timedelta = timedelta(days=1)

    def __post_init__(self) -> None:
        for field_name in (
            "base_equity_fraction",
            "maximum_market_fraction",
            "maximum_category_fraction",
            "maximum_total_exposure_fraction",
            "disagreement_reduction",
            "low_liquidity_reduction",
            "stale_data_reduction",
        ):
            _probability(getattr(self, field_name), field_name)
        _positive(self.minimum_stake, "minimum_stake")
        _positive(self.maximum_stake, "maximum_stake")
        _non_negative(self.low_liquidity_threshold, "low_liquidity_threshold")
        if self.minimum_stake > self.maximum_stake:
            raise PaperTradingInvariantError("minimum_stake cannot exceed maximum_stake")
        if self.stale_after <= timedelta(0):
            raise PaperTradingInvariantError("stale_after must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionSizingContext:
    equity: Decimal
    confidence: Decimal
    disagreement: Decimal
    liquidity: Decimal | None
    data_age: timedelta | None


class PositionSizingPolicy(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def configuration(self) -> PositionSizingConfiguration: ...

    def size(self, context: PositionSizingContext) -> Decimal: ...


class FixedFractionSizing:
    name = "fixed_fraction"
    version = "1.0.0"

    def __init__(
        self,
        configuration: PositionSizingConfiguration | None = None,
    ) -> None:
        self._configuration = configuration or PositionSizingConfiguration()

    @property
    def configuration(self) -> PositionSizingConfiguration:
        return self._configuration

    def size(self, context: PositionSizingContext) -> Decimal:
        _positive(context.equity, "equity")
        amount = context.equity * self.configuration.base_equity_fraction
        return _bounded_stake(amount, self.configuration)


class ConfidenceAdjustedSizing(FixedFractionSizing):
    name = "confidence_adjusted"
    version = "1.0.0"

    def size(self, context: PositionSizingContext) -> Decimal:
        _positive(context.equity, "equity")
        _probability(context.confidence, "confidence")
        _probability(context.disagreement, "disagreement")
        amount = context.equity * self.configuration.base_equity_fraction * context.confidence
        amount *= Decimal("1") - (context.disagreement * self.configuration.disagreement_reduction)
        if (
            context.liquidity is not None
            and context.liquidity < self.configuration.low_liquidity_threshold
        ):
            amount *= self.configuration.low_liquidity_reduction
        if context.data_age is not None and context.data_age > self.configuration.stale_after:
            amount *= self.configuration.stale_data_reduction
        return _bounded_stake(amount, self.configuration)


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskContext:
    equity: Decimal
    cash_balance: Decimal
    total_exposure: Decimal
    market_exposure: Decimal
    category_exposure: Decimal
    proposed_stake: Decimal
    correlated_exposure: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    approved_stake: Decimal
    rejection_reasons: tuple[str, ...]
    checks: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.approved_stake > 0 and not self.rejection_reasons


class RiskPolicy(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def assess(self, context: RiskContext) -> RiskAssessment: ...


class ConservativeRiskPolicy:
    name = "conservative_risk"
    version = "1.0.0"

    def __init__(self, configuration: PositionSizingConfiguration) -> None:
        self.configuration = configuration

    def assess(self, context: RiskContext) -> RiskAssessment:
        reasons: list[str] = []
        checks: list[str] = []
        proposed = context.proposed_stake
        if proposed < self.configuration.minimum_stake:
            reasons.append("stake_below_minimum")
        if proposed > self.configuration.maximum_stake:
            reasons.append("stake_above_maximum")
        if proposed > context.cash_balance:
            reasons.append("insufficient_capital")
        else:
            checks.append("capital:passed")
        if (
            context.market_exposure + proposed
            > context.equity * self.configuration.maximum_market_fraction
        ):
            reasons.append("maximum_market_exposure")
        else:
            checks.append("market_exposure:passed")
        if (
            context.category_exposure + proposed
            > context.equity * self.configuration.maximum_category_fraction
        ):
            reasons.append("category_concentration")
        else:
            checks.append("category_exposure:passed")
        if (
            context.total_exposure + proposed
            > context.equity * self.configuration.maximum_total_exposure_fraction
        ):
            reasons.append("maximum_total_exposure")
        else:
            checks.append("total_exposure:passed")
        if context.correlated_exposure > 0:
            reasons.append("correlated_market")
        else:
            checks.append("correlation:passed")
        return RiskAssessment(
            approved_stake=(proposed if not reasons else Decimal("0")),
            rejection_reasons=tuple(reasons),
            checks=tuple(checks),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConservativeCostConfiguration:
    percentage_fee: Decimal = Decimal("0.005")
    fixed_fee: Decimal = Decimal("0")
    slippage_probability_points: Decimal = Decimal("0.005")
    low_liquidity_penalty_points: Decimal = Decimal("0.005")
    stale_observation_penalty_points: Decimal = Decimal("0.005")
    low_liquidity_threshold: Decimal = Decimal("25")
    stale_after: timedelta = timedelta(days=1)

    def __post_init__(self) -> None:
        for field_name in (
            "percentage_fee",
            "slippage_probability_points",
            "low_liquidity_penalty_points",
            "stale_observation_penalty_points",
        ):
            _probability(getattr(self, field_name), field_name)
        _non_negative(self.fixed_fee, "fixed_fee")
        _non_negative(self.low_liquidity_threshold, "low_liquidity_threshold")
        if self.stale_after <= timedelta(0):
            raise PaperTradingInvariantError("stale_after must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    side: PositionSide
    market_probability: Decimal
    approved_stake: Decimal
    liquidity: Decimal | None
    data_age: timedelta | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperTradeExecution:
    side: PositionSide
    entry_probability: Decimal
    effective_probability: Decimal
    units: Decimal
    gross_cost: Decimal
    fees: Decimal
    slippage_cost: Decimal
    net_cost: Decimal
    maximum_loss: Decimal
    potential_payout: Decimal
    execution_model: str


class ExecutionCostModel(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def execute(self, context: ExecutionContext) -> PaperTradeExecution: ...


class ZeroCostModel:
    name = "zero_cost"
    version = "1.0.0"

    def execute(self, context: ExecutionContext) -> PaperTradeExecution:
        entry = _side_probability(context.side, context.market_probability)
        _tradable_probability(entry)
        _positive(context.approved_stake, "approved_stake")
        units = _amount(context.approved_stake / entry)
        gross = _amount(units * entry)
        return PaperTradeExecution(
            side=context.side,
            entry_probability=entry,
            effective_probability=entry,
            units=units,
            gross_cost=gross,
            fees=Decimal("0"),
            slippage_cost=Decimal("0"),
            net_cost=gross,
            maximum_loss=gross,
            potential_payout=units,
            execution_model=f"{self.name}:{self.version}",
        )


class ConservativeCostModel:
    name = "conservative_cost"
    version = "1.0.0"

    def __init__(
        self,
        configuration: ConservativeCostConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or ConservativeCostConfiguration()

    def execute(self, context: ExecutionContext) -> PaperTradeExecution:
        entry = _side_probability(context.side, context.market_probability)
        _tradable_probability(entry)
        _positive(context.approved_stake, "approved_stake")
        penalty = self.configuration.slippage_probability_points
        if (
            context.liquidity is not None
            and context.liquidity < self.configuration.low_liquidity_threshold
        ):
            penalty += self.configuration.low_liquidity_penalty_points
        if context.data_age is not None and context.data_age > self.configuration.stale_after:
            penalty += self.configuration.stale_observation_penalty_points
        effective = min(entry + penalty, _PROBABILITY_CEILING)
        budget = context.approved_stake
        if budget <= self.configuration.fixed_fee:
            raise PaperTradingInvariantError("approved stake cannot cover the simulated fixed fee")
        contract_budget = (budget - self.configuration.fixed_fee) / (
            Decimal("1") + self.configuration.percentage_fee
        )
        units = _amount(contract_budget / effective)
        gross = _amount(units * entry)
        slippage = _amount(units * (effective - entry))
        percentage_fee = _amount((gross + slippage) * self.configuration.percentage_fee)
        fees = _amount(self.configuration.fixed_fee + percentage_fee)
        net = gross + slippage + fees
        return PaperTradeExecution(
            side=context.side,
            entry_probability=entry,
            effective_probability=effective,
            units=units,
            gross_cost=gross,
            fees=fees,
            slippage_cost=slippage,
            net_cost=net,
            maximum_loss=net,
            potential_payout=units,
            execution_model=f"{self.name}:{self.version}",
        )


class TradingBaseline(Protocol):
    @property
    def name(self) -> str: ...

    def side_for(
        self,
        *,
        market_probability: Decimal,
        system_probability: Decimal,
        edge: Decimal,
    ) -> PositionSide | None: ...


class NoTradeBaseline:
    name = "no_trade"

    def side_for(
        self,
        *,
        market_probability: Decimal,
        system_probability: Decimal,
        edge: Decimal,
    ) -> PositionSide | None:
        del market_probability, system_probability, edge
        return None


class MarketFollowBaseline:
    name = "market_follow"

    def side_for(
        self,
        *,
        market_probability: Decimal,
        system_probability: Decimal,
        edge: Decimal,
    ) -> PositionSide | None:
        del system_probability, edge
        return PositionSide.YES if market_probability >= Decimal("0.5") else PositionSide.NO


class FixedThresholdBaseline:
    name = "fixed_threshold"

    def __init__(self, threshold: Decimal = Decimal("0.08")) -> None:
        _probability(threshold, "threshold")
        self.threshold = threshold

    def side_for(
        self,
        *,
        market_probability: Decimal,
        system_probability: Decimal,
        edge: Decimal,
    ) -> PositionSide | None:
        del market_probability, system_probability
        if abs(edge) < self.threshold:
            return None
        return PositionSide.YES if edge > 0 else PositionSide.NO


def _side_probability(side: PositionSide, market_probability: Decimal) -> Decimal:
    _probability(market_probability, "market_probability")
    return market_probability if side is PositionSide.YES else Decimal("1") - market_probability


def _bounded_stake(
    amount: Decimal,
    configuration: PositionSizingConfiguration,
) -> Decimal:
    return _amount(
        min(
            max(amount, configuration.minimum_stake),
            configuration.maximum_stake,
        )
    )


def _amount(value: Decimal) -> Decimal:
    return value.quantize(_AMOUNT_QUANTUM, rounding=ROUND_DOWN)


def _tradable_probability(value: Decimal) -> None:
    _probability(value, "entry_probability")
    if value <= 0 or value >= 1:
        raise PaperTradingInvariantError(
            "a simulated binary contract requires a probability strictly between 0 and 1"
        )


def _positive(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise PaperTradingInvariantError(f"{field_name} must be positive")


def _non_negative(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or value < 0:
        raise PaperTradingInvariantError(f"{field_name} cannot be negative")


def _probability(value: Decimal, field_name: str) -> None:
    if not value.is_finite() or not Decimal("0") <= value <= Decimal("1"):
        raise PaperTradingInvariantError(f"{field_name} must be between 0 and 1")
