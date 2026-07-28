"""Pure evaluation functions for simulated portfolios and trading baselines."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from predictionlab.domain.paper_trading.entities import PositionSide
from predictionlab.domain.paper_trading.policies import (
    ExecutionContext,
    ExecutionCostModel,
    TradingBaseline,
)


class SampleEvidenceState(StrEnum):
    INSUFFICIENT = "insufficient_sample"
    PRELIMINARY = "preliminary_result"
    OBSERVING = "under_observation"
    SUFFICIENT_TO_EXPAND = "sufficient_to_expand_validation"


@dataclass(frozen=True, slots=True, kw_only=True)
class StrategyBreakdown:
    key: str
    trade_count: int
    net_pnl: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperPerformanceMetrics:
    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    simulated_roi: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_costs: Decimal
    decision_count: int
    open_trade_count: int
    closed_trade_count: int
    abstention_count: int
    rejection_count: int
    win_rate: Decimal | None
    average_profit: Decimal | None
    average_loss: Decimal | None
    profit_factor: Decimal | None
    maximum_drawdown: Decimal
    maximum_exposure: Decimal
    coverage: Decimal
    independent_resolved_markets: int
    largest_trade_profit_share: Decimal
    evidence_state: SampleEvidenceState
    by_category: tuple[StrategyBreakdown, ...]
    by_opportunity_level: tuple[StrategyBreakdown, ...]
    by_edge_range: tuple[StrategyBreakdown, ...]
    by_confidence_range: tuple[StrategyBreakdown, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TradingSample:
    market_id: str
    category: str
    opportunity_level: str
    edge: Decimal
    confidence: Decimal
    realized_pnl: Decimal | None
    costs: Decimal
    outcome: str | None
    side: PositionSide | None


@dataclass(frozen=True, slots=True, kw_only=True)
class BaselinePerformance:
    name: str
    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    simulated_roi: Decimal
    trade_count: int
    total_costs: Decimal


def evaluate_performance(
    *,
    initial_capital: Decimal,
    final_equity: Decimal,
    realized_pnl: Decimal,
    unrealized_pnl: Decimal,
    decision_count: int,
    abstention_count: int,
    rejection_count: int,
    open_trade_count: int,
    samples: tuple[TradingSample, ...],
    equity_curve: tuple[Decimal, ...],
    exposure_curve: tuple[Decimal, ...],
    preliminary_threshold: int = 10,
    observation_threshold: int = 30,
    expansion_threshold: int = 100,
    maximum_concentration: Decimal = Decimal("0.25"),
) -> PaperPerformanceMetrics:
    closed = tuple(sample for sample in samples if sample.realized_pnl is not None)
    scored = tuple(
        sample for sample in closed if sample.outcome in {"yes", "no"}
    )
    profits = tuple(
        sample.realized_pnl
        for sample in scored
        if sample.realized_pnl is not None and sample.realized_pnl > 0
    )
    losses = tuple(
        sample.realized_pnl
        for sample in scored
        if sample.realized_pnl is not None and sample.realized_pnl < 0
    )
    total_profit = sum(profits, Decimal("0"))
    total_loss = abs(sum(losses, Decimal("0")))
    net_profit = final_equity - initial_capital
    roi = net_profit / initial_capital if initial_capital else Decimal("0")
    total_costs = sum((sample.costs for sample in samples), Decimal("0"))
    closed_count = len(closed)
    independent = len({sample.market_id for sample in scored})
    largest_share = (
        max(profits, default=Decimal("0")) / total_profit if total_profit > 0 else Decimal("0")
    )
    evidence_state = _evidence_state(
        independent=independent,
        closed_count=closed_count,
        largest_share=largest_share,
        maximum_drawdown=_maximum_drawdown(equity_curve),
        preliminary_threshold=preliminary_threshold,
        observation_threshold=observation_threshold,
        expansion_threshold=expansion_threshold,
        maximum_concentration=maximum_concentration,
    )
    executed = len(samples)
    return PaperPerformanceMetrics(
        initial_capital=initial_capital,
        final_capital=final_equity,
        net_profit=net_profit,
        simulated_roi=roi,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        total_costs=total_costs,
        decision_count=decision_count,
        open_trade_count=open_trade_count,
        closed_trade_count=closed_count,
        abstention_count=abstention_count,
        rejection_count=rejection_count,
        win_rate=(Decimal(len(profits)) / Decimal(len(scored)) if scored else None),
        average_profit=(total_profit / Decimal(len(profits)) if profits else None),
        average_loss=(sum(losses, Decimal("0")) / Decimal(len(losses)) if losses else None),
        profit_factor=(
            total_profit / total_loss
            if total_loss > 0
            else (None if total_profit == 0 else Decimal("999"))
        ),
        maximum_drawdown=_maximum_drawdown(equity_curve),
        maximum_exposure=max(exposure_curve, default=Decimal("0")),
        coverage=(Decimal(executed) / Decimal(decision_count) if decision_count else Decimal("0")),
        independent_resolved_markets=independent,
        largest_trade_profit_share=largest_share,
        evidence_state=evidence_state,
        by_category=_breakdown(samples, lambda sample: sample.category or "unknown"),
        by_opportunity_level=_breakdown(
            samples,
            lambda sample: sample.opportunity_level,
        ),
        by_edge_range=_breakdown(samples, lambda sample: _edge_range(sample.edge)),
        by_confidence_range=_breakdown(
            samples,
            lambda sample: _confidence_range(sample.confidence),
        ),
    )


def evaluate_baseline(
    *,
    baseline: TradingBaseline,
    samples: tuple[TradingSample, ...],
    market_probabilities: dict[str, Decimal],
    system_probabilities: dict[str, Decimal],
    outcomes: dict[str, str],
    initial_capital: Decimal,
    stake: Decimal,
    cost_model: ExecutionCostModel,
) -> BaselinePerformance:
    cash = initial_capital
    costs = Decimal("0")
    trades = 0
    seen: set[str] = set()
    for sample in samples:
        if sample.market_id in seen or sample.market_id not in outcomes:
            continue
        market_probability = market_probabilities[sample.market_id]
        system_probability = system_probabilities[sample.market_id]
        side = baseline.side_for(
            market_probability=market_probability,
            system_probability=system_probability,
            edge=system_probability - market_probability,
        )
        seen.add(sample.market_id)
        if side is None or cash < stake:
            continue
        outcome = outcomes[sample.market_id]
        if outcome in {"other", "unresolved"}:
            continue
        execution = cost_model.execute(
            ExecutionContext(
                side=side,
                market_probability=market_probability,
                approved_stake=stake,
                liquidity=None,
                data_age=None,
            )
        )
        cash -= execution.net_cost
        if outcome == "cancelled":
            cash += execution.net_cost
        else:
            won = (side is PositionSide.YES and outcome == "yes") or (
                side is PositionSide.NO and outcome == "no"
            )
            cash += execution.units if won else Decimal("0")
            costs += execution.fees + execution.slippage_cost
        trades += 1
    profit = cash - initial_capital
    return BaselinePerformance(
        name=baseline.name,
        initial_capital=initial_capital,
        final_capital=cash,
        net_profit=profit,
        simulated_roi=(profit / initial_capital if initial_capital else Decimal("0")),
        trade_count=trades,
        total_costs=costs,
    )


def _maximum_drawdown(equity_curve: tuple[Decimal, ...]) -> Decimal:
    peak = Decimal("0")
    maximum = Decimal("0")
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            maximum = max(maximum, (peak - equity) / peak)
    return maximum


def _breakdown(
    samples: tuple[TradingSample, ...],
    key: Callable[[TradingSample], str],
) -> tuple[StrategyBreakdown, ...]:
    counts: dict[str, int] = defaultdict(int)
    pnl: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for sample in samples:
        value = key(sample)
        counts[value] += 1
        if sample.realized_pnl is not None:
            pnl[value] += sample.realized_pnl
    return tuple(
        StrategyBreakdown(key=value, trade_count=counts[value], net_pnl=pnl[value])
        for value in sorted(counts)
    )


def _edge_range(edge: Decimal) -> str:
    absolute = abs(edge)
    if absolute < Decimal("0.05"):
        return "0-5pp"
    if absolute < Decimal("0.10"):
        return "5-10pp"
    if absolute < Decimal("0.20"):
        return "10-20pp"
    return "20pp+"


def _confidence_range(confidence: Decimal) -> str:
    if confidence < Decimal("0.50"):
        return "0-50%"
    if confidence < Decimal("0.70"):
        return "50-70%"
    if confidence < Decimal("0.85"):
        return "70-85%"
    return "85%+"


def _evidence_state(
    *,
    independent: int,
    closed_count: int,
    largest_share: Decimal,
    maximum_drawdown: Decimal,
    preliminary_threshold: int,
    observation_threshold: int,
    expansion_threshold: int,
    maximum_concentration: Decimal,
) -> SampleEvidenceState:
    sample = min(independent, closed_count)
    if sample < preliminary_threshold:
        return SampleEvidenceState.INSUFFICIENT
    if sample < observation_threshold:
        return SampleEvidenceState.PRELIMINARY
    if (
        sample >= expansion_threshold
        and largest_share <= maximum_concentration
        and maximum_drawdown <= Decimal("0.25")
    ):
        return SampleEvidenceState.SUFFICIENT_TO_EXPAND
    return SampleEvidenceState.OBSERVING
