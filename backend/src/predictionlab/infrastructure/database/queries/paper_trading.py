"""Read models and evaluation inputs for simulated trading."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.application.paper_trading import (
    EquityCurvePoint,
    ListPaperPortfolios,
    ListPaperPositions,
    ListPaperSettlements,
    ListPaperTrades,
    ListTradeDecisions,
    PaperPage,
    PaperPerformanceData,
    PaperPortfolioDetail,
    PaperPositionDetail,
    PaperSettlementDetail,
    PaperTradeDetail,
    TradeDecisionDetail,
)
from predictionlab.domain.markets import ResolutionOutcome
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolioStatus,
    PaperPositionStatus,
    PositionSide,
    TradeDecisionType,
    TradingSample,
)
from predictionlab.domain.predictions import OpportunityLevel
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    PaperOrderModel,
    PaperPerformanceSnapshotModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperSettlementModel,
    PaperTradeModel,
    PredictionRunModel,
    TradeDecisionModel,
)


class SqlAlchemyPaperTradingReadRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list_portfolios(
        self,
        query: ListPaperPortfolios,
    ) -> PaperPage[PaperPortfolioDetail]:
        statement = select(PaperPortfolioModel)
        if query.status is not None:
            statement = statement.where(
                PaperPortfolioModel.status == query.status.value
            )
        if query.experiment_run_id is not None:
            statement = statement.where(
                PaperPortfolioModel.experiment_run_id == query.experiment_run_id
            )
        if query.currency_unit is not None:
            statement = statement.where(
                PaperPortfolioModel.currency_unit == query.currency_unit.value
            )
        async with self._session_factory() as session:
            total = await _count(session, statement)
            rows = (
                await session.scalars(
                    statement.order_by(
                        PaperPortfolioModel.created_at.desc(),
                        PaperPortfolioModel.portfolio_id,
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PaperPage(
            tuple(_portfolio(item) for item in rows),
            query.page,
            query.page_size,
            total,
        )

    async def get_portfolio(self, portfolio_id: UUID) -> PaperPortfolioDetail | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(PaperPortfolioModel).where(
                    PaperPortfolioModel.portfolio_id == portfolio_id
                )
            )
        return _portfolio(model) if model is not None else None

    async def list_decisions(
        self,
        query: ListTradeDecisions,
    ) -> PaperPage[TradeDecisionDetail]:
        statement = (
            select(TradeDecisionModel, PredictionRunModel, MarketModel)
            .join(
                PredictionRunModel,
                PredictionRunModel.prediction_run_id
                == TradeDecisionModel.prediction_run_id,
            )
            .join(MarketModel, MarketModel.market_id == PredictionRunModel.market_id)
        )
        if query.portfolio_id is not None:
            statement = statement.where(
                TradeDecisionModel.portfolio_id == query.portfolio_id
            )
        if query.market_id is not None:
            statement = statement.where(MarketModel.market_id == query.market_id)
        if query.category is not None:
            statement = statement.where(MarketModel.category == query.category)
        if query.side is not None:
            statement = statement.where(TradeDecisionModel.side == query.side.value)
        if query.decision is not None:
            statement = statement.where(
                TradeDecisionModel.decision == query.decision.value
            )
        if query.opportunity_level is not None:
            statement = statement.where(
                TradeDecisionModel.opportunity_level
                == query.opportunity_level.value
            )
        if query.experiment_run_id is not None:
            statement = statement.where(
                TradeDecisionModel.experiment_run_id == query.experiment_run_id
            )
        if query.decided_from is not None:
            statement = statement.where(
                TradeDecisionModel.decided_at >= query.decided_from
            )
        if query.decided_to is not None:
            statement = statement.where(
                TradeDecisionModel.decided_at <= query.decided_to
            )
        async with self._session_factory() as session:
            total = await _count(session, statement)
            rows = (
                await session.execute(
                    statement.order_by(
                        TradeDecisionModel.decided_at.desc(),
                        TradeDecisionModel.decision_id,
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PaperPage(
            tuple(_decision(*row) for row in rows),
            query.page,
            query.page_size,
            total,
        )

    async def list_trades(
        self,
        query: ListPaperTrades,
    ) -> PaperPage[PaperTradeDetail]:
        statement = _trade_statement()
        if query.portfolio_id is not None:
            statement = statement.where(PaperOrderModel.portfolio_id == query.portfolio_id)
        if query.market_id is not None:
            statement = statement.where(MarketModel.market_id == query.market_id)
        if query.category is not None:
            statement = statement.where(MarketModel.category == query.category)
        if query.side is not None:
            statement = statement.where(PaperTradeModel.side == query.side.value)
        if query.experiment_run_id is not None:
            statement = statement.where(
                TradeDecisionModel.experiment_run_id == query.experiment_run_id
            )
        if query.executed_from is not None:
            statement = statement.where(
                PaperTradeModel.executed_at >= query.executed_from
            )
        if query.executed_to is not None:
            statement = statement.where(
                PaperTradeModel.executed_at <= query.executed_to
            )
        async with self._session_factory() as session:
            total = await _count(session, statement)
            rows = (
                await session.execute(
                    statement.order_by(
                        PaperTradeModel.executed_at.desc(),
                        PaperTradeModel.trade_id,
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PaperPage(
            tuple(_trade_detail(*row) for row in rows),
            query.page,
            query.page_size,
            total,
        )

    async def get_trade(self, trade_id: UUID) -> PaperTradeDetail | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    _trade_statement().where(PaperTradeModel.trade_id == trade_id)
                )
            ).one_or_none()
        return _trade_detail(*row) if row is not None else None

    async def list_positions(
        self,
        query: ListPaperPositions,
    ) -> PaperPage[PaperPositionDetail]:
        statement = _position_statement()
        if query.portfolio_id is not None:
            statement = statement.where(
                PaperPositionModel.portfolio_id == query.portfolio_id
            )
        if query.market_id is not None:
            statement = statement.where(
                PaperPositionModel.market_id == query.market_id
            )
        if query.category is not None:
            statement = statement.where(
                PaperPositionModel.category == query.category
            )
        if query.side is not None:
            statement = statement.where(PaperPositionModel.side == query.side.value)
        if query.status is not None:
            statement = statement.where(
                PaperPositionModel.status == query.status.value
            )
        if query.experiment_run_id is not None:
            statement = statement.where(
                PaperPortfolioModel.experiment_run_id == query.experiment_run_id
            )
        async with self._session_factory() as session:
            total = await _count(session, statement)
            rows = (
                await session.execute(
                    statement.order_by(
                        PaperPositionModel.opened_at.desc(),
                        PaperPositionModel.position_id,
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PaperPage(
            tuple(_position_detail(*row) for row in rows),
            query.page,
            query.page_size,
            total,
        )

    async def get_position(self, position_id: UUID) -> PaperPositionDetail | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    _position_statement().where(
                        PaperPositionModel.position_id == position_id
                    )
                )
            ).one_or_none()
        return _position_detail(*row) if row is not None else None

    async def list_settlements(
        self,
        query: ListPaperSettlements,
    ) -> PaperPage[PaperSettlementDetail]:
        statement = _settlement_statement()
        if query.portfolio_id is not None:
            statement = statement.where(
                PaperPositionModel.portfolio_id == query.portfolio_id
            )
        if query.market_id is not None:
            statement = statement.where(
                PaperSettlementModel.market_id == query.market_id
            )
        if query.outcome is not None:
            statement = statement.where(
                PaperSettlementModel.outcome == query.outcome.value
            )
        if query.experiment_run_id is not None:
            statement = statement.where(
                PaperPortfolioModel.experiment_run_id == query.experiment_run_id
            )
        if query.resolved_from is not None:
            statement = statement.where(
                PaperSettlementModel.resolved_at >= query.resolved_from
            )
        if query.resolved_to is not None:
            statement = statement.where(
                PaperSettlementModel.resolved_at <= query.resolved_to
            )
        async with self._session_factory() as session:
            total = await _count(session, statement)
            rows = (
                await session.execute(
                    statement.order_by(
                        PaperSettlementModel.resolved_at.desc(),
                        PaperSettlementModel.settlement_id,
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PaperPage(
            tuple(_settlement_detail(*row) for row in rows),
            query.page,
            query.page_size,
            total,
        )

    async def equity_curve(self, portfolio_id: UUID) -> tuple[EquityCurvePoint, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(PaperPerformanceSnapshotModel)
                    .where(
                        PaperPerformanceSnapshotModel.portfolio_id == portfolio_id
                    )
                    .order_by(
                        PaperPerformanceSnapshotModel.recorded_at,
                        PaperPerformanceSnapshotModel.snapshot_id,
                    )
                )
            ).all()
        return tuple(_equity_point(item) for item in rows)

    async def performance_data(
        self,
        portfolio_id: UUID,
    ) -> PaperPerformanceData | None:
        async with self._session_factory() as session:
            portfolio_model = await session.scalar(
                select(PaperPortfolioModel).where(
                    PaperPortfolioModel.portfolio_id == portfolio_id
                )
            )
            if portfolio_model is None:
                return None
            decisions = (
                await session.execute(
                    select(TradeDecisionModel, PredictionRunModel, MarketModel)
                    .join(
                        PredictionRunModel,
                        PredictionRunModel.prediction_run_id
                        == TradeDecisionModel.prediction_run_id,
                    )
                    .join(
                        MarketModel,
                        MarketModel.market_id == PredictionRunModel.market_id,
                    )
                    .where(TradeDecisionModel.portfolio_id == portfolio_id)
                    .order_by(
                        TradeDecisionModel.decided_at,
                        TradeDecisionModel.decision_id,
                    )
                )
            ).all()
            position_rows = (
                await session.execute(
                    select(PaperPositionModel, PaperTradeModel)
                    .join(
                        PaperTradeModel,
                        PaperTradeModel.trade_id == PaperPositionModel.trade_id,
                    )
                    .where(PaperPositionModel.portfolio_id == portfolio_id)
                    .order_by(
                        PaperPositionModel.opened_at,
                        PaperPositionModel.position_id,
                    )
                )
            ).all()
            curve_models = (
                await session.scalars(
                    select(PaperPerformanceSnapshotModel)
                    .where(
                        PaperPerformanceSnapshotModel.portfolio_id == portfolio_id
                    )
                    .order_by(
                        PaperPerformanceSnapshotModel.recorded_at,
                        PaperPerformanceSnapshotModel.snapshot_id,
                    )
                )
            ).all()
            latest_recorded_at = (
                curve_models[-1].recorded_at
                if curve_models
                else portfolio_model.updated_at
            )
            samples = tuple(
                TradingSample(
                    market_id=str(position.market_id),
                    category=position.category or "unknown",
                    opportunity_level=position.opportunity_level,
                    edge=position.entry_edge,
                    confidence=position.entry_confidence,
                    realized_pnl=(
                        position.realized_pnl
                        if position.status
                        in {
                            PaperPositionStatus.SETTLED.value,
                            PaperPositionStatus.CANCELLED.value,
                        }
                        else None
                    ),
                    costs=trade.fees + trade.slippage_cost,
                    outcome=position.settlement_outcome,
                    side=PositionSide(position.side),
                )
                for position, trade in position_rows
            )
            baseline_samples = tuple(
                TradingSample(
                    market_id=str(market.market_id),
                    category=market.category or "unknown",
                    opportunity_level=decision.opportunity_level,
                    edge=decision.edge or Decimal("0"),
                    confidence=decision.confidence,
                    realized_pnl=None,
                    costs=Decimal("0"),
                    outcome=(
                        market.resolution_outcome
                        if market.resolution_outcome
                        in {
                            ResolutionOutcome.YES.value,
                            ResolutionOutcome.NO.value,
                            ResolutionOutcome.CANCELLED.value,
                        }
                        else None
                    ),
                    side=None,
                )
                for decision, prediction, market in decisions
                if prediction.market_probability is not None
                and prediction.consensus_probability is not None
            )
            market_probabilities = {
                str(market.market_id): prediction.market_probability
                for _, prediction, market in decisions
                if prediction.market_probability is not None
            }
            system_probabilities = {
                str(market.market_id): prediction.consensus_probability
                for _, prediction, market in decisions
                if prediction.consensus_probability is not None
            }
            outcomes = {
                str(market.market_id): market.resolution_outcome
                for _, _, market in decisions
                if market.resolution_outcome
                in {
                    ResolutionOutcome.YES.value,
                    ResolutionOutcome.NO.value,
                    ResolutionOutcome.CANCELLED.value,
                }
            }
            open_positions = tuple(
                position
                for position, _ in position_rows
                if position.status == PaperPositionStatus.OPEN.value
            )
            category_exposure: dict[str, Decimal] = {}
            for position in open_positions:
                key = position.category or "unknown"
                category_exposure[key] = (
                    category_exposure.get(key, Decimal("0"))
                    + position.invested_amount
                )
            maximum_category_concentration = (
                max(category_exposure.values(), default=Decimal("0"))
                / portfolio_model.equity
                if portfolio_model.equity > 0
                else Decimal("0")
            )
            terminal = tuple(
                position
                for position, _ in reversed(position_rows)
                if position.status
                in {
                    PaperPositionStatus.SETTLED.value,
                    PaperPositionStatus.CANCELLED.value,
                }
            )
            consecutive_losses = 0
            for position in terminal:
                if position.realized_pnl >= 0:
                    break
                consecutive_losses += 1
            unsettled_resolved_count = 0
            other_pending_count = 0
            stale_open_count = 0
            for position in open_positions:
                market = await session.get(MarketModel, position.market_id)
                if market is None:
                    continue
                if market.resolution_outcome in {
                    ResolutionOutcome.YES.value,
                    ResolutionOutcome.NO.value,
                    ResolutionOutcome.CANCELLED.value,
                }:
                    unsettled_resolved_count += 1
                if market.resolution_outcome == ResolutionOutcome.OTHER.value:
                    other_pending_count += 1
                latest_observed_at = await session.scalar(
                    select(func.max(MarketObservationModel.observed_at)).where(
                        MarketObservationModel.market_id == position.market_id,
                        MarketObservationModel.observed_at <= latest_recorded_at,
                        MarketObservationModel.probability.is_not(None),
                    )
                )
                if (
                    latest_observed_at is None
                    or latest_recorded_at - latest_observed_at > timedelta(days=2)
                ):
                    stale_open_count += 1
            decision_count = len(decisions)
            abstention_count = sum(
                decision.decision == TradeDecisionType.ABSTAIN.value
                for decision, _, _ in decisions
            )
            rejection_count = sum(
                decision.decision == TradeDecisionType.REJECTED.value
                for decision, _, _ in decisions
            )
        return PaperPerformanceData(
            portfolio=_portfolio(portfolio_model),
            decision_count=decision_count,
            abstention_count=abstention_count,
            rejection_count=rejection_count,
            open_position_count=len(open_positions),
            samples=samples,
            baseline_samples=baseline_samples,
            equity_curve=tuple(_equity_point(item) for item in curve_models),
            market_probabilities=market_probabilities,
            system_probabilities=system_probabilities,
            outcomes=outcomes,
            maximum_category_concentration=maximum_category_concentration,
            consecutive_losses=consecutive_losses,
            unsettled_resolved_count=unsettled_resolved_count,
            other_pending_count=other_pending_count,
            stale_open_count=stale_open_count,
        )


async def _count(session: AsyncSession, statement: Select[Any]) -> int:
    value = await session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    return int(value or 0)


def _trade_statement() -> Select[
    tuple[
        PaperTradeModel,
        PaperOrderModel,
        TradeDecisionModel,
        PredictionRunModel,
        MarketModel,
    ]
]:
    return (
        select(
            PaperTradeModel,
            PaperOrderModel,
            TradeDecisionModel,
            PredictionRunModel,
            MarketModel,
        )
        .join(PaperOrderModel, PaperOrderModel.order_id == PaperTradeModel.order_id)
        .join(
            TradeDecisionModel,
            TradeDecisionModel.decision_id == PaperOrderModel.decision_id,
        )
        .join(
            PredictionRunModel,
            PredictionRunModel.prediction_run_id
            == TradeDecisionModel.prediction_run_id,
        )
        .join(MarketModel, MarketModel.market_id == PredictionRunModel.market_id)
    )


def _position_statement() -> Select[
    tuple[PaperPositionModel, MarketModel, PaperPortfolioModel]
]:
    return (
        select(PaperPositionModel, MarketModel, PaperPortfolioModel)
        .join(MarketModel, MarketModel.market_id == PaperPositionModel.market_id)
        .join(
            PaperPortfolioModel,
            PaperPortfolioModel.portfolio_id == PaperPositionModel.portfolio_id,
        )
    )


def _settlement_statement() -> Select[
    tuple[
        PaperSettlementModel,
        PaperPositionModel,
        MarketModel,
        PaperPortfolioModel,
    ]
]:
    return (
        select(
            PaperSettlementModel,
            PaperPositionModel,
            MarketModel,
            PaperPortfolioModel,
        )
        .join(
            PaperPositionModel,
            PaperPositionModel.position_id == PaperSettlementModel.position_id,
        )
        .join(MarketModel, MarketModel.market_id == PaperSettlementModel.market_id)
        .join(
            PaperPortfolioModel,
            PaperPortfolioModel.portfolio_id == PaperPositionModel.portfolio_id,
        )
    )


def _portfolio(model: PaperPortfolioModel) -> PaperPortfolioDetail:
    return PaperPortfolioDetail(
        portfolio_id=model.portfolio_id,
        name=model.name,
        currency_unit=CurrencyUnit(model.currency_unit),
        initial_balance=model.initial_balance,
        cash_balance=model.cash_balance,
        reserved_balance=model.reserved_balance,
        realized_pnl=model.realized_pnl,
        unrealized_pnl=model.unrealized_pnl,
        equity=model.equity,
        total_exposure=model.total_exposure,
        status=PaperPortfolioStatus(model.status),
        strategy_configuration_hash=model.strategy_configuration_hash,
        experiment_run_id=model.experiment_run_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _decision(
    decision: TradeDecisionModel,
    prediction: PredictionRunModel,
    market: MarketModel,
) -> TradeDecisionDetail:
    return TradeDecisionDetail(
        decision_id=decision.decision_id,
        prediction_run_id=decision.prediction_run_id,
        portfolio_id=decision.portfolio_id,
        market_id=market.market_id,
        market_title=market.title,
        category=market.category,
        decided_at=decision.decided_at,
        decision=TradeDecisionType(decision.decision),
        side=PositionSide(decision.side) if decision.side is not None else None,
        market_probability=decision.market_probability,
        system_probability=decision.system_probability,
        edge=decision.edge,
        confidence=decision.confidence,
        opportunity_level=OpportunityLevel(decision.opportunity_level),
        proposed_stake=decision.proposed_stake,
        approved_stake=decision.approved_stake,
        rejection_reasons=tuple(decision.rejection_reasons),
        risk_checks=tuple(decision.risk_checks),
        configuration_hash=decision.configuration_hash,
        result_hash=decision.result_hash,
        correlation_id=decision.correlation_id,
        causation_id=decision.causation_id,
        experiment_run_id=decision.experiment_run_id,
        prediction_result_hash=prediction.result_hash,
    )


def _trade_detail(
    trade: PaperTradeModel,
    order: PaperOrderModel,
    decision: TradeDecisionModel,
    prediction: PredictionRunModel,
    market: MarketModel,
) -> PaperTradeDetail:
    return PaperTradeDetail(
        trade_id=trade.trade_id,
        order_id=trade.order_id,
        decision_id=decision.decision_id,
        portfolio_id=order.portfolio_id,
        prediction_run_id=order.prediction_run_id,
        market_id=market.market_id,
        market_title=market.title,
        category=market.category,
        executed_at=trade.executed_at,
        side=PositionSide(trade.side),
        entry_probability=trade.entry_probability,
        effective_probability=trade.effective_probability,
        units=trade.units,
        gross_cost=trade.gross_cost,
        fees=trade.fees,
        slippage_cost=trade.slippage_cost,
        net_cost=trade.net_cost,
        maximum_loss=trade.maximum_loss,
        potential_payout=trade.potential_payout,
        execution_model=trade.execution_model,
        result_hash=trade.result_hash,
        decision_reasons=tuple(decision.risk_checks),
        prediction_result_hash=prediction.result_hash,
        experiment_run_id=decision.experiment_run_id,
    )


def _position_detail(
    position: PaperPositionModel,
    market: MarketModel,
    portfolio: PaperPortfolioModel,
) -> PaperPositionDetail:
    return PaperPositionDetail(
        position_id=position.position_id,
        portfolio_id=position.portfolio_id,
        market_id=position.market_id,
        market_title=market.title,
        category=position.category,
        side=PositionSide(position.side),
        opened_at=position.opened_at,
        closed_at=position.closed_at,
        status=PaperPositionStatus(position.status),
        units=position.units,
        average_entry_probability=position.average_entry_probability,
        invested_amount=position.invested_amount,
        current_mark_probability=position.current_mark_probability,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        settlement_outcome=(
            ResolutionOutcome(position.settlement_outcome)
            if position.settlement_outcome is not None
            else None
        ),
        prediction_run_id=position.prediction_run_id,
        trade_id=position.trade_id,
        opportunity_level=OpportunityLevel(position.opportunity_level),
        entry_edge=position.entry_edge,
        entry_confidence=position.entry_confidence,
        experiment_run_id=portfolio.experiment_run_id,
    )


def _settlement_detail(
    settlement: PaperSettlementModel,
    position: PaperPositionModel,
    market: MarketModel,
    portfolio: PaperPortfolioModel,
) -> PaperSettlementDetail:
    return PaperSettlementDetail(
        settlement_id=settlement.settlement_id,
        position_id=settlement.position_id,
        portfolio_id=position.portfolio_id,
        market_id=settlement.market_id,
        market_title=market.title,
        resolved_at=settlement.resolved_at,
        outcome=ResolutionOutcome(settlement.outcome),
        gross_payout=settlement.gross_payout,
        fees=settlement.fees,
        net_payout=settlement.net_payout,
        realized_pnl=settlement.realized_pnl,
        settlement_policy=settlement.settlement_policy,
        result_hash=settlement.result_hash,
        created_at=settlement.created_at,
        correlation_id=settlement.correlation_id,
        causation_id=settlement.causation_id,
        experiment_run_id=portfolio.experiment_run_id,
    )


def _equity_point(model: PaperPerformanceSnapshotModel) -> EquityCurvePoint:
    return EquityCurvePoint(
        recorded_at=model.recorded_at,
        equity=model.equity,
        drawdown=model.drawdown,
        exposure=model.total_exposure,
        realized_pnl=model.realized_pnl,
        unrealized_pnl=model.unrealized_pnl,
        cumulative_costs=model.cumulative_costs,
        result_hash=model.result_hash,
    )
