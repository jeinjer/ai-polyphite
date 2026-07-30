"""Composition helpers for deterministic simulated portfolio execution."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.application.commercial_evaluations import (
    CommercialEvaluationService,
)
from predictionlab.application.paper_trading import (
    PaperTradingOrchestrator,
    PaperTradingUnitOfWork,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.settings import Settings
from predictionlab.domain.paper_trading import (
    ConfidenceAdjustedSizing,
    ConservativeCostConfiguration,
    ConservativeCostModel,
    ConservativeRiskPolicy,
    ExecutionCostModel,
    FixedFractionSizing,
    PositionSizingConfiguration,
    PositionSizingPolicy,
    ThresholdEntryConfiguration,
    ThresholdEntryPolicy,
    ZeroCostModel,
)
from predictionlab.domain.predictions import OpportunityLevel
from predictionlab.infrastructure.database.paper_trading_unit_of_work import (
    SqlAlchemyPaperTradingUnitOfWork,
)


def create_paper_trading_orchestrator(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    clock: Clock | None = None,
    campaign_id: str = "conservative-v1",
    minimum_entry_edge: Decimal | None = None,
    minimum_net_edge: Decimal = Decimal("0"),
) -> PaperTradingOrchestrator:
    sizing_configuration = PositionSizingConfiguration(
        base_equity_fraction=settings.paper_base_equity_fraction,
        minimum_stake=settings.paper_minimum_stake,
        maximum_stake=settings.paper_maximum_stake,
        maximum_market_fraction=settings.paper_maximum_market_fraction,
        maximum_category_fraction=settings.paper_maximum_category_fraction,
        maximum_total_exposure_fraction=settings.paper_maximum_total_exposure_fraction,
        disagreement_reduction=settings.paper_disagreement_reduction,
        low_liquidity_reduction=settings.paper_low_liquidity_reduction,
        stale_data_reduction=settings.paper_stale_data_reduction,
        low_liquidity_threshold=settings.paper_low_liquidity_threshold,
        stale_after=timedelta(seconds=settings.paper_sizing_stale_after_seconds),
    )
    sizing_policy: PositionSizingPolicy = (
        FixedFractionSizing(sizing_configuration)
        if settings.paper_sizing_policy == "fixed_fraction"
        else ConfidenceAdjustedSizing(sizing_configuration)
    )
    cost_model = create_paper_cost_model(settings)

    def unit_of_work() -> PaperTradingUnitOfWork:
        return cast(
            PaperTradingUnitOfWork,
            SqlAlchemyPaperTradingUnitOfWork(session_factory),
        )

    return PaperTradingOrchestrator(
        unit_of_work=unit_of_work,
        entry_policy=ThresholdEntryPolicy(
            ThresholdEntryConfiguration(
                minimum_absolute_edge=(
                    settings.paper_entry_minimum_edge
                    if minimum_entry_edge is None
                    else minimum_entry_edge
                ),
                minimum_confidence=settings.paper_entry_minimum_confidence,
                maximum_data_age=timedelta(seconds=settings.paper_maximum_data_age_seconds),
                allowed_opportunity_levels=(
                    frozenset(OpportunityLevel)
                    if minimum_entry_edge == Decimal("0")
                    else ThresholdEntryConfiguration().allowed_opportunity_levels
                ),
                allow_yes=settings.paper_allow_yes,
                allow_no=settings.paper_allow_no,
                minimum_stake=settings.paper_minimum_stake,
                maximum_stake=settings.paper_maximum_stake,
            )
        ),
        sizing_policy=sizing_policy,
        risk_policy=ConservativeRiskPolicy(sizing_configuration),
        cost_model=cost_model,
        clock=clock or SystemClock(),
        commercial_evaluation_service=CommercialEvaluationService(
            campaign_id=campaign_id,
            minimum_net_edge=minimum_net_edge,
            minimum_confidence=settings.paper_entry_minimum_confidence,
            maximum_data_age=timedelta(seconds=settings.paper_maximum_data_age_seconds),
            percentage_fee=(
                Decimal("0")
                if settings.paper_cost_model == "zero"
                else settings.paper_percentage_fee
            ),
            fixed_fee=(
                Decimal("0") if settings.paper_cost_model == "zero" else settings.paper_fixed_fee
            ),
            slippage_probability_points=(
                Decimal("0")
                if settings.paper_cost_model == "zero"
                else settings.paper_slippage_probability_points
            ),
            low_liquidity_penalty_points=(
                Decimal("0")
                if settings.paper_cost_model == "zero"
                else settings.paper_low_liquidity_penalty_points
            ),
            stale_observation_penalty_points=(
                Decimal("0")
                if settings.paper_cost_model == "zero"
                else settings.paper_stale_observation_penalty_points
            ),
            low_liquidity_threshold=settings.paper_low_liquidity_threshold,
            cost_stale_after=timedelta(seconds=settings.paper_sizing_stale_after_seconds),
        ),
    )


def create_paper_cost_model(settings: Settings) -> ExecutionCostModel:
    """Build the exact cost model shared by execution and baseline evaluation."""
    return (
        ZeroCostModel()
        if settings.paper_cost_model == "zero"
        else ConservativeCostModel(
            ConservativeCostConfiguration(
                percentage_fee=settings.paper_percentage_fee,
                fixed_fee=settings.paper_fixed_fee,
                slippage_probability_points=(settings.paper_slippage_probability_points),
                low_liquidity_penalty_points=(settings.paper_low_liquidity_penalty_points),
                stale_observation_penalty_points=(settings.paper_stale_observation_penalty_points),
                low_liquidity_threshold=settings.paper_low_liquidity_threshold,
                stale_after=timedelta(seconds=settings.paper_sizing_stale_after_seconds),
            )
        )
    )
