"""SQLAlchemy adapter for transactional simulated portfolio accounting."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from predictionlab.application.paper_trading import (
    OpenPositionContext,
    PaperTradingIdempotencyConflictError,
    PaperTradingOutcome,
    PortfolioExposure,
    TradingPredictionContext,
)
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperLedgerEntry,
    PaperOrder,
    PaperOrderStatus,
    PaperPerformanceSnapshot,
    PaperPortfolio,
    PaperPortfolioStatus,
    PaperPosition,
    PaperPositionStatus,
    PaperSettlement,
    PaperTrade,
    PositionSide,
    TradeDecision,
    TradeDecisionType,
)
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus
from predictionlab.infrastructure.database.models import (
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PaperLedgerEntryModel,
    PaperOrderModel,
    PaperPerformanceSnapshotModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperSettlementModel,
    PaperTradeModel,
    PredictionRunModel,
    TradeDecisionModel,
)


class SqlAlchemyPaperTradingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_portfolio(
        self,
        portfolio_id: UUID,
        *,
        for_update: bool = False,
    ) -> PaperPortfolio | None:
        statement = select(PaperPortfolioModel).where(
            PaperPortfolioModel.portfolio_id == portfolio_id
        )
        if for_update:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _portfolio(model) if model is not None else None

    async def find_experiment_portfolio(
        self,
        *,
        experiment_run_id: UUID,
        strategy_configuration_hash: str,
    ) -> PaperPortfolio | None:
        model = await self._session.scalar(
            select(PaperPortfolioModel).where(
                PaperPortfolioModel.experiment_run_id == experiment_run_id,
                PaperPortfolioModel.strategy_configuration_hash == strategy_configuration_hash,
            )
        )
        return _portfolio(model) if model is not None else None

    async def find_live_portfolio(
        self,
        *,
        name: str,
        currency_unit: CurrencyUnit,
        strategy_configuration_hash: str,
    ) -> PaperPortfolio | None:
        model = (
            await self._session.scalars(
                select(PaperPortfolioModel)
                .where(
                    PaperPortfolioModel.experiment_run_id.is_(None),
                    PaperPortfolioModel.name == name,
                    PaperPortfolioModel.currency_unit == currency_unit.value,
                    PaperPortfolioModel.strategy_configuration_hash
                    == strategy_configuration_hash,
                )
                .order_by(
                    PaperPortfolioModel.created_at,
                    PaperPortfolioModel.portfolio_id,
                )
                .limit(1)
            )
        ).first()
        return _portfolio(model) if model is not None else None

    async def add_portfolio(self, portfolio: PaperPortfolio) -> None:
        self._session.add(
            PaperPortfolioModel(
                portfolio_id=portfolio.portfolio_id,
                name=portfolio.name,
                currency_unit=portfolio.currency_unit.value,
                initial_balance=portfolio.initial_balance,
                cash_balance=portfolio.cash_balance,
                reserved_balance=portfolio.reserved_balance,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl,
                equity=portfolio.equity,
                total_exposure=portfolio.total_exposure,
                status=portfolio.status.value,
                strategy_configuration_hash=portfolio.strategy_configuration_hash,
                experiment_run_id=portfolio.experiment_run_id,
                created_at=portfolio.created_at,
                updated_at=portfolio.updated_at,
            )
        )
        await self._session.flush()

    async def update_portfolio(self, portfolio: PaperPortfolio) -> None:
        await self._session.execute(
            update(PaperPortfolioModel)
            .where(PaperPortfolioModel.portfolio_id == portfolio.portfolio_id)
            .values(
                cash_balance=portfolio.cash_balance,
                reserved_balance=portfolio.reserved_balance,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl,
                equity=portfolio.equity,
                total_exposure=portfolio.total_exposure,
                status=portfolio.status.value,
                updated_at=portfolio.updated_at,
            )
        )
        await self._session.flush()

    async def prediction_context(
        self,
        prediction_run_id: UUID,
    ) -> TradingPredictionContext | None:
        row = (
            await self._session.execute(
                select(PredictionRunModel, MarketModel)
                .join(
                    MarketModel,
                    MarketModel.market_id == PredictionRunModel.market_id,
                )
                .where(PredictionRunModel.prediction_run_id == prediction_run_id)
            )
        ).one_or_none()
        if row is None:
            return None
        prediction, market = row
        market_status = await self._market_status_as_of(
            market.market_id,
            prediction.predicted_at,
        )
        probability_observation = (
            await self._session.scalars(
                select(MarketObservationModel)
                .where(
                    MarketObservationModel.market_id == market.market_id,
                    MarketObservationModel.observed_at <= prediction.predicted_at,
                    MarketObservationModel.probability.is_not(None),
                )
                .order_by(
                    MarketObservationModel.observed_at.desc(),
                    MarketObservationModel.observation_id.desc(),
                )
                .limit(1)
            )
        ).first()
        liquidity = await self._session.scalar(
            select(MarketObservationModel.liquidity)
            .where(
                MarketObservationModel.market_id == market.market_id,
                MarketObservationModel.observed_at <= prediction.predicted_at,
                MarketObservationModel.liquidity.is_not(None),
            )
            .order_by(
                MarketObservationModel.observed_at.desc(),
                MarketObservationModel.observation_id.desc(),
            )
            .limit(1)
        )
        return TradingPredictionContext(
            prediction_run_id=prediction.prediction_run_id,
            prediction_result_hash=prediction.result_hash,
            experiment_run_id=prediction.experiment_run_id,
            market_id=market.market_id,
            market_title=market.title,
            category=market.category,
            predicted_at=prediction.predicted_at,
            prediction_status=PredictionRunStatus(prediction.status),
            market_probability=prediction.market_probability,
            system_probability=prediction.consensus_probability,
            edge=prediction.edge,
            confidence=prediction.consensus_confidence,
            opportunity_level=OpportunityLevel(prediction.opportunity_level),
            disagreement_score=prediction.disagreement_score,
            market_status_as_of=market_status,
            observation_at=(
                probability_observation.observed_at if probability_observation is not None else None
            ),
            liquidity=liquidity,
        )

    async def find_outcome(
        self,
        *,
        portfolio_id: UUID,
        prediction_run_id: UUID,
    ) -> PaperTradingOutcome | None:
        decision_model = await self._session.scalar(
            select(TradeDecisionModel).where(
                TradeDecisionModel.portfolio_id == portfolio_id,
                TradeDecisionModel.prediction_run_id == prediction_run_id,
            )
        )
        if decision_model is None:
            return None
        order_model = await self._session.scalar(
            select(PaperOrderModel).where(PaperOrderModel.decision_id == decision_model.decision_id)
        )
        trade_model = None
        position_model = None
        if order_model is not None:
            trade_model = await self._session.scalar(
                select(PaperTradeModel).where(PaperTradeModel.order_id == order_model.order_id)
            )
            if trade_model is not None:
                position_model = await self._session.scalar(
                    select(PaperPositionModel).where(
                        PaperPositionModel.trade_id == trade_model.trade_id
                    )
                )
        return PaperTradingOutcome(
            decision=_decision(decision_model),
            order=_order(order_model) if order_model is not None else None,
            trade=_trade(trade_model) if trade_model is not None else None,
            position=(_position(position_model) if position_model is not None else None),
        )

    async def exposure(
        self,
        *,
        portfolio_id: UUID,
        market_id: UUID,
        category: str | None,
    ) -> PortfolioExposure:
        base = select(func.coalesce(func.sum(PaperPositionModel.invested_amount), 0)).where(
            PaperPositionModel.portfolio_id == portfolio_id,
            PaperPositionModel.status == PaperPositionStatus.OPEN.value,
        )
        total = await self._session.scalar(base)
        market = await self._session.scalar(base.where(PaperPositionModel.market_id == market_id))
        category_value = await self._session.scalar(
            base.where(
                PaperPositionModel.category == category
                if category is not None
                else PaperPositionModel.category.is_(None)
            )
        )
        return PortfolioExposure(
            total=Decimal(total or 0),
            market=Decimal(market or 0),
            category=Decimal(category_value or 0),
        )

    async def add_decision(self, decision: TradeDecision) -> None:
        side = _decision_side(decision)
        self._session.add(
            TradeDecisionModel(
                decision_id=decision.decision_id,
                prediction_run_id=decision.prediction_run_id,
                portfolio_id=decision.portfolio_id,
                decided_at=decision.decided_at,
                decision=decision.decision.value,
                side=side.value if side is not None else None,
                market_probability=decision.market_probability,
                system_probability=decision.system_probability,
                edge=decision.edge,
                confidence=decision.confidence,
                opportunity_level=decision.opportunity_level,
                proposed_stake=decision.proposed_stake,
                approved_stake=decision.approved_stake,
                rejection_reasons=list(decision.rejection_reasons),
                risk_checks=list(decision.risk_checks),
                configuration_hash=decision.configuration_hash,
                result_hash=decision.result_hash,
                correlation_id=decision.correlation_id,
                causation_id=decision.causation_id,
                experiment_run_id=decision.experiment_run_id,
            )
        )
        await self._session.flush()

    async def add_order(self, order: PaperOrder) -> None:
        self._session.add(
            PaperOrderModel(
                order_id=order.order_id,
                decision_id=order.decision_id,
                portfolio_id=order.portfolio_id,
                prediction_run_id=order.prediction_run_id,
                market_id=order.market_id,
                side=order.side.value,
                requested_at=order.requested_at,
                requested_stake=order.requested_stake,
                status=order.status.value,
                rejection_reason=order.rejection_reason,
                configuration_hash=order.configuration_hash,
            )
        )
        await self._session.flush()

    async def add_trade(self, trade: PaperTrade) -> None:
        self._session.add(
            PaperTradeModel(
                trade_id=trade.trade_id,
                order_id=trade.order_id,
                executed_at=trade.executed_at,
                side=trade.side.value,
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
            )
        )
        await self._session.flush()

    async def add_position(self, position: PaperPosition) -> None:
        self._session.add(_position_model(position))
        await self._session.flush()

    async def update_position(self, position: PaperPosition) -> None:
        await self._session.execute(
            update(PaperPositionModel)
            .where(PaperPositionModel.position_id == position.position_id)
            .values(
                closed_at=position.closed_at,
                status=position.status.value,
                current_mark_probability=position.current_mark_probability,
                unrealized_pnl=position.unrealized_pnl,
                realized_pnl=position.realized_pnl,
                settlement_outcome=position.settlement_outcome,
            )
        )
        await self._session.flush()

    async def add_settlement(self, settlement: PaperSettlement) -> None:
        self._session.add(
            PaperSettlementModel(
                settlement_id=settlement.settlement_id,
                position_id=settlement.position_id,
                market_id=settlement.market_id,
                resolved_at=settlement.resolved_at,
                outcome=settlement.outcome,
                gross_payout=settlement.gross_payout,
                fees=settlement.fees,
                net_payout=settlement.net_payout,
                realized_pnl=settlement.realized_pnl,
                settlement_policy=settlement.settlement_policy,
                result_hash=settlement.result_hash,
                created_at=settlement.created_at,
                correlation_id=settlement.correlation_id,
                causation_id=settlement.causation_id,
            )
        )
        await self._session.flush()

    async def add_ledger_entry(self, entry: PaperLedgerEntry) -> None:
        self._session.add(
            PaperLedgerEntryModel(
                ledger_entry_id=entry.ledger_entry_id,
                portfolio_id=entry.portfolio_id,
                entry_type=entry.entry_type.value,
                occurred_at=entry.occurred_at,
                amount=entry.amount,
                cash_balance_after=entry.cash_balance_after,
                reserved_balance_after=entry.reserved_balance_after,
                equity_after=entry.equity_after,
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                result_hash=entry.result_hash,
            )
        )
        await self._session.flush()

    async def add_performance_snapshot(
        self,
        snapshot: PaperPerformanceSnapshot,
    ) -> PaperPerformanceSnapshot:
        existing = await self._session.scalar(
            select(PaperPerformanceSnapshotModel).where(
                PaperPerformanceSnapshotModel.portfolio_id == snapshot.portfolio_id,
                PaperPerformanceSnapshotModel.recorded_at == snapshot.recorded_at,
            )
        )
        if existing is not None:
            if existing.result_hash != snapshot.result_hash:
                raise PaperTradingIdempotencyConflictError(
                    "performance snapshot scope contains different results"
                )
            return _performance_snapshot(existing)
        self._session.add(_performance_snapshot_model(snapshot))
        await self._session.flush()
        return snapshot

    async def open_positions(
        self,
        *,
        portfolio_id: UUID,
        as_of: datetime,
    ) -> tuple[OpenPositionContext, ...]:
        rows = (
            await self._session.execute(
                select(PaperPositionModel, MarketModel)
                .join(MarketModel, MarketModel.market_id == PaperPositionModel.market_id)
                .where(
                    PaperPositionModel.portfolio_id == portfolio_id,
                    PaperPositionModel.status == PaperPositionStatus.OPEN.value,
                )
                .order_by(
                    PaperPositionModel.opened_at,
                    PaperPositionModel.position_id,
                )
            )
        ).all()
        contexts: list[OpenPositionContext] = []
        for position_model, market in rows:
            visible_resolution = market.resolved_at is not None and market.resolved_at <= as_of
            observation = (
                await self._session.scalars(
                    select(MarketObservationModel)
                    .where(
                        MarketObservationModel.market_id == market.market_id,
                        MarketObservationModel.observed_at <= as_of,
                        MarketObservationModel.probability.is_not(None),
                    )
                    .order_by(
                        MarketObservationModel.observed_at.desc(),
                        MarketObservationModel.observation_id.desc(),
                    )
                    .limit(1)
                )
            ).first()
            contexts.append(
                OpenPositionContext(
                    position=_position(position_model),
                    market_status=(
                        MarketStatus(market.status)
                        if visible_resolution
                        else await self._market_status_as_of(market.market_id, as_of)
                    ),
                    resolution_outcome=(
                        ResolutionOutcome(market.resolution_outcome)
                        if visible_resolution
                        else ResolutionOutcome.UNRESOLVED
                    ),
                    resolved_at=market.resolved_at if visible_resolution else None,
                    latest_probability=(
                        observation.probability if observation is not None else None
                    ),
                    observation_at=(observation.observed_at if observation is not None else None),
                )
            )
        return tuple(contexts)

    async def performance_counters(
        self,
        portfolio_id: UUID,
    ) -> tuple[int, int, int]:
        open_count = await self._session.scalar(
            select(func.count())
            .select_from(PaperPositionModel)
            .where(
                PaperPositionModel.portfolio_id == portfolio_id,
                PaperPositionModel.status == PaperPositionStatus.OPEN.value,
            )
        )
        closed_count = await self._session.scalar(
            select(func.count())
            .select_from(PaperPositionModel)
            .where(
                PaperPositionModel.portfolio_id == portfolio_id,
                PaperPositionModel.status.in_(
                    (
                        PaperPositionStatus.SETTLED.value,
                        PaperPositionStatus.CANCELLED.value,
                    )
                ),
            )
        )
        decision_count = await self._session.scalar(
            select(func.count())
            .select_from(TradeDecisionModel)
            .where(TradeDecisionModel.portfolio_id == portfolio_id)
        )
        return int(open_count or 0), int(closed_count or 0), int(decision_count or 0)

    async def cumulative_costs(self, portfolio_id: UUID) -> Decimal:
        value = await self._session.scalar(
            select(
                func.coalesce(
                    func.sum(PaperTradeModel.fees + PaperTradeModel.slippage_cost),
                    0,
                )
            )
            .join(PaperOrderModel, PaperOrderModel.order_id == PaperTradeModel.order_id)
            .where(PaperOrderModel.portfolio_id == portfolio_id)
        )
        return Decimal(value or 0)

    async def maximum_equity(self, portfolio_id: UUID) -> Decimal:
        value = await self._session.scalar(
            select(func.max(PaperPerformanceSnapshotModel.equity)).where(
                PaperPerformanceSnapshotModel.portfolio_id == portfolio_id
            )
        )
        return Decimal(value or 0)

    async def _market_status_as_of(
        self,
        market_id: UUID,
        as_of: datetime,
    ) -> MarketStatus:
        value = await self._session.scalar(
            select(MarketStateChangeModel.status)
            .where(
                MarketStateChangeModel.market_id == market_id,
                MarketStateChangeModel.occurred_at <= as_of,
            )
            .order_by(
                MarketStateChangeModel.occurred_at.desc(),
                MarketStateChangeModel.change_id.desc(),
            )
            .limit(1)
        )
        if value is not None:
            return MarketStatus(value)
        raise RuntimeError(
            "market has no state history visible at prediction time; "
            "paper execution stopped to preserve the anti-lookahead boundary"
        )


def _portfolio(model: PaperPortfolioModel) -> PaperPortfolio:
    return PaperPortfolio(
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


def _decision(model: TradeDecisionModel) -> TradeDecision:
    return TradeDecision(
        decision_id=model.decision_id,
        prediction_run_id=model.prediction_run_id,
        portfolio_id=model.portfolio_id,
        decided_at=model.decided_at,
        decision=TradeDecisionType(model.decision),
        market_probability=model.market_probability,
        system_probability=model.system_probability,
        edge=model.edge,
        confidence=model.confidence,
        opportunity_level=model.opportunity_level,
        proposed_stake=model.proposed_stake,
        approved_stake=model.approved_stake,
        rejection_reasons=tuple(model.rejection_reasons),
        risk_checks=tuple(model.risk_checks),
        configuration_hash=model.configuration_hash,
        result_hash=model.result_hash,
        correlation_id=model.correlation_id,
        causation_id=model.causation_id,
        experiment_run_id=model.experiment_run_id,
    )


def _order(model: PaperOrderModel) -> PaperOrder:
    return PaperOrder(
        order_id=model.order_id,
        decision_id=model.decision_id,
        portfolio_id=model.portfolio_id,
        prediction_run_id=model.prediction_run_id,
        market_id=model.market_id,
        side=PositionSide(model.side),
        requested_at=model.requested_at,
        requested_stake=model.requested_stake,
        status=PaperOrderStatus(model.status),
        rejection_reason=model.rejection_reason,
        configuration_hash=model.configuration_hash,
    )


def _trade(model: PaperTradeModel) -> PaperTrade:
    return PaperTrade(
        trade_id=model.trade_id,
        order_id=model.order_id,
        executed_at=model.executed_at,
        side=PositionSide(model.side),
        entry_probability=model.entry_probability,
        effective_probability=model.effective_probability,
        units=model.units,
        gross_cost=model.gross_cost,
        fees=model.fees,
        slippage_cost=model.slippage_cost,
        net_cost=model.net_cost,
        maximum_loss=model.maximum_loss,
        potential_payout=model.potential_payout,
        execution_model=model.execution_model,
        result_hash=model.result_hash,
    )


def _position(model: PaperPositionModel) -> PaperPosition:
    return PaperPosition(
        position_id=model.position_id,
        portfolio_id=model.portfolio_id,
        market_id=model.market_id,
        category=model.category,
        side=PositionSide(model.side),
        opened_at=model.opened_at,
        closed_at=model.closed_at,
        status=PaperPositionStatus(model.status),
        units=model.units,
        average_entry_probability=model.average_entry_probability,
        invested_amount=model.invested_amount,
        current_mark_probability=model.current_mark_probability,
        unrealized_pnl=model.unrealized_pnl,
        realized_pnl=model.realized_pnl,
        settlement_outcome=model.settlement_outcome,
        prediction_run_id=model.prediction_run_id,
        trade_id=model.trade_id,
        opportunity_level=model.opportunity_level,
        entry_edge=model.entry_edge,
        entry_confidence=model.entry_confidence,
    )


def _position_model(position: PaperPosition) -> PaperPositionModel:
    return PaperPositionModel(
        position_id=position.position_id,
        portfolio_id=position.portfolio_id,
        market_id=position.market_id,
        category=position.category,
        side=position.side.value,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
        status=position.status.value,
        units=position.units,
        average_entry_probability=position.average_entry_probability,
        invested_amount=position.invested_amount,
        current_mark_probability=position.current_mark_probability,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        settlement_outcome=position.settlement_outcome,
        prediction_run_id=position.prediction_run_id,
        trade_id=position.trade_id,
        opportunity_level=position.opportunity_level,
        entry_edge=position.entry_edge,
        entry_confidence=position.entry_confidence,
    )


def _performance_snapshot(
    model: PaperPerformanceSnapshotModel,
) -> PaperPerformanceSnapshot:
    return PaperPerformanceSnapshot(
        snapshot_id=model.snapshot_id,
        portfolio_id=model.portfolio_id,
        recorded_at=model.recorded_at,
        cash_balance=model.cash_balance,
        reserved_balance=model.reserved_balance,
        realized_pnl=model.realized_pnl,
        unrealized_pnl=model.unrealized_pnl,
        equity=model.equity,
        total_exposure=model.total_exposure,
        cumulative_costs=model.cumulative_costs,
        drawdown=model.drawdown,
        open_positions=model.open_positions,
        closed_positions=model.closed_positions,
        configuration_hash=model.configuration_hash,
        result_hash=model.result_hash,
    )


def _performance_snapshot_model(
    snapshot: PaperPerformanceSnapshot,
) -> PaperPerformanceSnapshotModel:
    return PaperPerformanceSnapshotModel(
        snapshot_id=snapshot.snapshot_id,
        portfolio_id=snapshot.portfolio_id,
        recorded_at=snapshot.recorded_at,
        cash_balance=snapshot.cash_balance,
        reserved_balance=snapshot.reserved_balance,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        equity=snapshot.equity,
        total_exposure=snapshot.total_exposure,
        cumulative_costs=snapshot.cumulative_costs,
        drawdown=snapshot.drawdown,
        open_positions=snapshot.open_positions,
        closed_positions=snapshot.closed_positions,
        configuration_hash=snapshot.configuration_hash,
        result_hash=snapshot.result_hash,
    )


def _decision_side(decision: TradeDecision) -> PositionSide | None:
    if decision.decision is TradeDecisionType.BUY_YES:
        return PositionSide.YES
    if decision.decision is TradeDecisionType.BUY_NO:
        return PositionSide.NO
    if decision.proposed_stake > 0 and decision.edge is not None:
        return PositionSide.YES if decision.edge > 0 else PositionSide.NO
    return None
