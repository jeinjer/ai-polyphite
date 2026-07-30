"""Transactional paper trading orchestration over persisted predictions."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from predictionlab.application.commercial_evaluations import (
    CommercialEvaluationService,
    EvaluateCommercialOpportunity,
)
from predictionlab.application.paper_trading.models import (
    CreatePaperPortfolio,
    CreatePaperPortfolioResult,
    ManualPaperTradeResult,
    ManualPaperTradeStatus,
    PaperTradingOutcome,
    PortfolioExposure,
    RunManualPaperTrade,
    RunPaperTrading,
    SettlementBatchResult,
    SettlePaperPortfolio,
    TradingPredictionContext,
)
from predictionlab.application.paper_trading.repository import (
    PaperTradingRepository,
    PaperTradingUnitOfWork,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.markets import ResolutionOutcome
from predictionlab.domain.paper_trading import (
    ConfidenceAdjustedSizing,
    ConservativeCostModel,
    ConservativeRiskPolicy,
    EntryAssessment,
    EntryPolicy,
    ExecutionContext,
    ExecutionCostModel,
    LedgerEntryType,
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
    PositionSizingContext,
    PositionSizingPolicy,
    RiskContext,
    RiskPolicy,
    ThresholdEntryPolicy,
    TradeDecision,
    TradeDecisionSource,
    TradeDecisionType,
)
from predictionlab.domain.paper_trading.policies import EntryContext

logger = logging.getLogger(__name__)


class PaperPortfolioNotFoundError(Exception):
    pass


class PredictionRunNotFoundError(Exception):
    pass


class PaperTradingConfigurationError(Exception):
    pass


class PaperTradingIdempotencyConflictError(Exception):
    pass


class PaperTradingOrchestrator:
    """Apply explicit policies without any real execution capability."""

    def __init__(
        self,
        *,
        unit_of_work: Callable[[], PaperTradingUnitOfWork],
        entry_policy: EntryPolicy | None = None,
        sizing_policy: PositionSizingPolicy | None = None,
        risk_policy: RiskPolicy | None = None,
        cost_model: ExecutionCostModel | None = None,
        clock: Clock | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        cancelled_settlement_policy: str = "refund_net_cost",
        commercial_evaluation_service: CommercialEvaluationService | None = None,
    ) -> None:
        sizing = sizing_policy or ConfidenceAdjustedSizing()
        self._unit_of_work = unit_of_work
        self._entry_policy = entry_policy or ThresholdEntryPolicy()
        self._sizing_policy = sizing
        self._risk_policy = risk_policy or ConservativeRiskPolicy(sizing.configuration)
        self._cost_model = cost_model or ConservativeCostModel()
        self._clock = clock or SystemClock()
        self._id_factory = id_factory
        self._commercial_evaluations = commercial_evaluation_service
        entry_configuration = getattr(self._entry_policy, "configuration", None)
        self._maximum_data_age = getattr(
            entry_configuration,
            "maximum_data_age",
            timedelta(days=2),
        )
        if cancelled_settlement_policy != "refund_net_cost":
            raise PaperTradingConfigurationError("unsupported cancelled settlement policy")
        self._cancelled_settlement_policy = cancelled_settlement_policy
        self._configuration_payload = self._resolved_configuration()
        self.configuration_hash = canonical_sha256(self._configuration_payload)

    def now(self) -> datetime:
        return self._clock.now()

    async def create_portfolio(
        self,
        command: CreatePaperPortfolio,
    ) -> CreatePaperPortfolioResult:
        now = self._clock.now()
        correlation_id = command.correlation_id or str(self._id_factory())
        async with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.paper_trading
            if command.experiment_run_id is not None:
                existing = await repository.find_experiment_portfolio(
                    experiment_run_id=command.experiment_run_id,
                    strategy_configuration_hash=self.configuration_hash,
                )
                if existing is not None:
                    _assert_compatible_portfolio(existing, command)
                    await unit_of_work.commit()
                    return CreatePaperPortfolioResult(existing, False)
            else:
                existing = await repository.find_live_portfolio(
                    name=command.name,
                    currency_unit=command.currency_unit,
                    strategy_configuration_hash=self.configuration_hash,
                )
                if existing is not None:
                    _assert_compatible_portfolio(existing, command)
                    await unit_of_work.commit()
                    return CreatePaperPortfolioResult(existing, False)
            portfolio = PaperPortfolio(
                portfolio_id=self._id_factory(),
                name=command.name,
                currency_unit=command.currency_unit,
                initial_balance=command.initial_balance,
                cash_balance=command.initial_balance,
                reserved_balance=Decimal("0"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                equity=command.initial_balance,
                total_exposure=Decimal("0"),
                status=PaperPortfolioStatus.ACTIVE,
                strategy_configuration_hash=self.configuration_hash,
                experiment_run_id=command.experiment_run_id,
                created_at=now,
                updated_at=now,
            )
            await repository.add_portfolio(portfolio)
            await repository.add_ledger_entry(
                PaperLedgerEntry(
                    ledger_entry_id=self._id_factory(),
                    portfolio_id=portfolio.portfolio_id,
                    entry_type=LedgerEntryType.INITIAL_CAPITAL,
                    occurred_at=now,
                    amount=command.initial_balance,
                    cash_balance_after=portfolio.cash_balance,
                    reserved_balance_after=portfolio.reserved_balance,
                    equity_after=portfolio.equity,
                    reference_type="portfolio",
                    reference_id=portfolio.portfolio_id,
                    result_hash=canonical_sha256(
                        {
                            "type": LedgerEntryType.INITIAL_CAPITAL,
                            "currency_unit": portfolio.currency_unit,
                            "amount": command.initial_balance,
                            "configuration_hash": self.configuration_hash,
                        }
                    ),
                )
            )
            await unit_of_work.commit()
        logger.info(
            "paper_portfolio_created",
            extra={
                "portfolio_id": str(portfolio.portfolio_id),
                "experiment_run_id": (
                    str(portfolio.experiment_run_id) if portfolio.experiment_run_id else None
                ),
                "currency_unit": portfolio.currency_unit.value,
                "configuration_hash": self.configuration_hash,
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
                "simulation_only": True,
            },
        )
        return CreatePaperPortfolioResult(portfolio, True)

    async def run(self, command: RunPaperTrading) -> PaperTradingOutcome:
        correlation_id = command.correlation_id or str(self._id_factory())
        logger.info(
            "paper_trading_decision_started",
            extra={
                "portfolio_id": str(command.portfolio_id),
                "prediction_run_id": str(command.prediction_run_id),
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
                "simulation_only": True,
            },
        )
        async with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.paper_trading
            existing = await repository.find_outcome(
                portfolio_id=command.portfolio_id,
                prediction_run_id=command.prediction_run_id,
            )
            if existing is not None:
                await unit_of_work.commit()
                return existing
            portfolio = await repository.get_portfolio(
                command.portfolio_id,
                for_update=True,
            )
            if portfolio is None:
                raise PaperPortfolioNotFoundError(str(command.portfolio_id))
            context = await repository.prediction_context(command.prediction_run_id)
            if context is None:
                raise PredictionRunNotFoundError(str(command.prediction_run_id))
            _assert_experiment_compatibility(portfolio, context)
            decided_at = command.decided_at or context.predicted_at
            if decided_at != context.predicted_at:
                raise PaperTradingConfigurationError(
                    "MVP paper decisions must occur at PredictionRun.predicted_at"
                )
            exposure = await repository.exposure(
                portfolio_id=portfolio.portfolio_id,
                market_id=context.market_id,
                category=context.category,
            )
            assessment = self._entry_policy.evaluate(
                EntryContext(
                    prediction_status=context.prediction_status,
                    market_is_open=context.market_status_as_of.value == "open",
                    market_probability=context.market_probability,
                    system_probability=context.system_probability,
                    yes_edge=context.edge,
                    confidence=context.confidence,
                    opportunity_level=context.opportunity_level,
                    data_age=(
                        decided_at - context.observation_at
                        if context.observation_at is not None
                        else None
                    ),
                    has_existing_position=exposure.market > 0,
                    data_complete=(
                        context.market_probability is not None
                        and context.system_probability is not None
                        and context.edge is not None
                        and context.observation_at is not None
                    ),
                )
            )
            outcome = await self._apply_assessment(
                repository=repository,
                portfolio=portfolio,
                context=context,
                assessment=assessment,
                exposure=exposure,
                decided_at=decided_at,
                correlation_id=correlation_id,
                causation_id=command.causation_id,
            )
            await unit_of_work.commit()
        logger.info(
            "paper_trading_decision_finished",
            extra={
                "decision_id": str(outcome.decision.decision_id),
                "decision": outcome.decision.decision.value,
                "trade_id": (str(outcome.trade.trade_id) if outcome.trade is not None else None),
                "result_hash": outcome.decision.result_hash,
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
                "simulation_only": True,
            },
        )
        return outcome

    async def run_batch(
        self,
        *,
        portfolio_id: UUID,
        prediction_run_ids: Sequence[UUID],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> tuple[PaperTradingOutcome, ...]:
        resolved_correlation = correlation_id or str(self._id_factory())
        return tuple(
            [
                await self.run(
                    RunPaperTrading(
                        portfolio_id=portfolio_id,
                        prediction_run_id=prediction_run_id,
                        correlation_id=resolved_correlation,
                        causation_id=causation_id,
                    )
                )
                for prediction_run_id in prediction_run_ids
            ]
        )

    async def run_manual_override(
        self,
        command: RunManualPaperTrade,
    ) -> ManualPaperTradeResult:
        """Execute an explicit simulated override without agent trade gating."""

        correlation_id = command.correlation_id or str(self._id_factory())
        decided_at = command.decided_at or self._clock.now()
        async with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.paper_trading
            duplicate = await repository.find_outcome_by_idempotency(
                portfolio_id=command.portfolio_id,
                idempotency_key=command.idempotency_key,
            )
            if duplicate is not None:
                _assert_compatible_manual_override(duplicate, command)
            else:
                duplicate = await repository.find_outcome(
                    portfolio_id=command.portfolio_id,
                    prediction_run_id=command.prediction_run_id,
                )
                if duplicate is not None:
                    _assert_compatible_manual_override(duplicate, command)
            if duplicate is not None:
                await unit_of_work.commit()
                return ManualPaperTradeResult(
                    ManualPaperTradeStatus.DUPLICATE,
                    duplicate,
                )
            portfolio = await repository.get_portfolio(
                command.portfolio_id,
                for_update=True,
            )
            if portfolio is None:
                raise PaperPortfolioNotFoundError(str(command.portfolio_id))
            context = await repository.prediction_context(
                command.prediction_run_id,
                as_of=decided_at,
            )
            if context is None:
                raise PredictionRunNotFoundError(str(command.prediction_run_id))
            if portfolio.experiment_run_id != context.experiment_run_id:
                raise PaperTradingConfigurationError(
                    "portfolio and prediction belong to incompatible experiments"
                )
            exposure = await repository.exposure(
                portfolio_id=portfolio.portfolio_id,
                market_id=context.market_id,
                category=context.category,
            )
            reasons: list[str] = []
            checks: list[str] = ["manual_override:confirmed"]
            if portfolio.status is not PaperPortfolioStatus.ACTIVE:
                reasons.append("portfolio_inactive")
            else:
                checks.append("portfolio_status:passed")
            if portfolio.strategy_configuration_hash != self.configuration_hash:
                reasons.append("portfolio_configuration_mismatch")
            else:
                checks.append("portfolio_configuration:passed")
            if context.market_status_as_of.value != "open":
                reasons.append("market_closed_or_resolved")
            else:
                checks.append("market_status:passed")
            if context.market_probability is None or context.observation_at is None:
                reasons.append("missing_current_observation")
            else:
                checks.append("current_observation:passed")
                if decided_at - context.observation_at > self._maximum_data_age:
                    reasons.append("stale_observation")
                else:
                    checks.append("data_freshness:passed")
            if exposure.market > 0:
                reasons.append("incompatible_existing_position")
            else:
                checks.append("position_uniqueness:passed")
            assessment = EntryAssessment(
                decision=(
                    TradeDecisionType.BUY_YES
                    if command.side is PositionSide.YES
                    else TradeDecisionType.BUY_NO
                ),
                side=command.side,
                rejection_reasons=tuple(reasons),
                checks=tuple(checks),
            )
            outcome = await self._apply_assessment(
                repository=repository,
                portfolio=portfolio,
                context=context,
                assessment=assessment,
                exposure=exposure,
                decided_at=decided_at,
                correlation_id=correlation_id,
                causation_id=command.causation_id,
                requested_stake=command.requested_stake,
                decision_source=TradeDecisionSource.MANUAL_OVERRIDE,
                override_reason=command.override_reason,
                idempotency_key=command.idempotency_key,
                skip_commercial_gate=True,
            )
            await unit_of_work.commit()
        logger.info(
            "manual_paper_override_finished",
            extra={
                "prediction_run_id": str(command.prediction_run_id),
                "portfolio_id": str(command.portfolio_id),
                "trade_decision_id": str(outcome.decision.decision_id),
                "paper_trade_id": (
                    str(outcome.trade.trade_id) if outcome.trade is not None else None
                ),
                "status": (
                    ManualPaperTradeStatus.FILLED.value
                    if outcome.trade is not None
                    else ManualPaperTradeStatus.REJECTED.value
                ),
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
                "decision_source": TradeDecisionSource.MANUAL_OVERRIDE.value,
                "simulation_only": True,
            },
        )
        return ManualPaperTradeResult(
            (
                ManualPaperTradeStatus.FILLED
                if outcome.trade is not None
                else ManualPaperTradeStatus.REJECTED
            ),
            outcome,
        )

    async def settle(
        self,
        command: SettlePaperPortfolio,
    ) -> SettlementBatchResult:
        correlation_id = command.correlation_id or str(self._id_factory())
        async with self._unit_of_work() as unit_of_work:
            repository = unit_of_work.paper_trading
            portfolio = await repository.get_portfolio(
                command.portfolio_id,
                for_update=True,
            )
            if portfolio is None:
                raise PaperPortfolioNotFoundError(str(command.portfolio_id))
            contexts = await repository.open_positions(
                portfolio_id=portfolio.portfolio_id,
                as_of=command.settled_at,
            )
            settlements: list[PaperSettlement] = []
            for context in contexts:
                position = context.position
                if (
                    context.resolution_outcome is ResolutionOutcome.OTHER
                    or context.resolution_outcome is ResolutionOutcome.UNRESOLVED
                ):
                    if context.latest_probability is not None:
                        marked = position.mark(
                            probability=context.latest_probability,
                            marked_at=command.settled_at,
                        )
                        portfolio = portfolio.update_mark(
                            previous_unrealized_pnl=position.unrealized_pnl,
                            current_unrealized_pnl=marked.unrealized_pnl,
                            occurred_at=command.settled_at,
                        )
                        await repository.update_position(marked)
                    continue
                if context.resolved_at is None or context.resolved_at > command.settled_at:
                    continue
                settlement = self._settlement(
                    position=position,
                    outcome=context.resolution_outcome,
                    resolved_at=context.resolved_at,
                    created_at=command.settled_at,
                    correlation_id=correlation_id,
                    causation_id=command.causation_id,
                )
                terminal_position = position.settle(
                    outcome=context.resolution_outcome.value,
                    closed_at=context.resolved_at,
                    realized_pnl=settlement.realized_pnl,
                    cancelled=(context.resolution_outcome is ResolutionOutcome.CANCELLED),
                )
                portfolio = portfolio.settle_position(
                    invested_amount=position.invested_amount,
                    previous_unrealized_pnl=position.unrealized_pnl,
                    net_payout=settlement.net_payout,
                    realized_pnl=settlement.realized_pnl,
                    occurred_at=command.settled_at,
                )
                await repository.add_settlement(settlement)
                await repository.update_position(terminal_position)
                await repository.update_portfolio(portfolio)
                await repository.add_ledger_entry(
                    self._settlement_ledger(
                        portfolio=portfolio,
                        settlement=settlement,
                    )
                )
                settlements.append(settlement)
            await repository.update_portfolio(portfolio)
            performance_snapshot = await self._performance_snapshot(
                repository=repository,
                portfolio=portfolio,
                recorded_at=command.settled_at,
            )
            await unit_of_work.commit()
        logger.info(
            "paper_settlement_batch_finished",
            extra={
                "portfolio_id": str(portfolio.portfolio_id),
                "settlement_count": len(settlements),
                "equity": str(portfolio.equity),
                "result_hash": performance_snapshot.result_hash,
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
                "simulation_only": True,
            },
        )
        return SettlementBatchResult(tuple(settlements), performance_snapshot)

    async def _apply_assessment(
        self,
        *,
        repository: PaperTradingRepository,
        portfolio: PaperPortfolio,
        context: TradingPredictionContext,
        assessment: EntryAssessment,
        exposure: PortfolioExposure,
        decided_at: datetime,
        correlation_id: str,
        causation_id: str | None,
        requested_stake: Decimal | None = None,
        decision_source: TradeDecisionSource = TradeDecisionSource.AUTOMATIC,
        override_reason: str | None = None,
        idempotency_key: str | None = None,
        skip_commercial_gate: bool = False,
    ) -> PaperTradingOutcome:
        proposed = Decimal("0")
        approved = Decimal("0")
        reasons = list(assessment.rejection_reasons)
        checks = list(assessment.checks)
        side = assessment.side
        if assessment.approved and side is not None:
            proposed = (
                requested_stake
                if requested_stake is not None
                else self._sizing_policy.size(
                    PositionSizingContext(
                        equity=portfolio.equity,
                        confidence=context.confidence,
                        disagreement=context.disagreement_score,
                        liquidity=context.liquidity,
                        data_age=(
                            decided_at - context.observation_at
                            if context.observation_at is not None
                            else None
                        ),
                    )
                )
            )
            risk = self._risk_policy.assess(
                RiskContext(
                    equity=portfolio.equity,
                    cash_balance=portfolio.cash_balance,
                    total_exposure=exposure.total,
                    market_exposure=exposure.market,
                    category_exposure=exposure.category,
                    proposed_stake=proposed,
                )
            )
            approved = risk.approved_stake
            reasons.extend(risk.rejection_reasons)
            checks.extend(risk.checks)
        evaluation = None
        if self._commercial_evaluations is not None and not skip_commercial_gate:
            evaluation = self._commercial_evaluations.evaluate(
                EvaluateCommercialOpportunity(
                    prediction_run_id=context.prediction_run_id,
                    portfolio_id=portfolio.portfolio_id,
                    evaluated_at=decided_at,
                    prediction_status=context.prediction_status,
                    estimated_outcome=context.estimated_outcome,
                    market_probability=context.market_probability,
                    consensus_probability=context.system_probability,
                    confidence=context.confidence,
                    market_is_open=(context.market_status_as_of.value == "open"),
                    data_age=(
                        decided_at - context.observation_at
                        if context.observation_at is not None
                        else None
                    ),
                    liquidity=context.liquidity,
                    proposed_stake=proposed,
                    portfolio_is_active=(portfolio.status is PaperPortfolioStatus.ACTIVE),
                    portfolio_has_open_position=exposure.market > 0,
                    entry_reasons=tuple(assessment.rejection_reasons),
                    risk_reasons=tuple(
                        reason for reason in reasons if reason not in assessment.rejection_reasons
                    ),
                )
            )
            await repository.add_commercial_evaluation(evaluation)
            if assessment.approved and side is not None and not evaluation.is_actionable:
                reasons.extend(evaluation.reasons)
                reasons.append("commercial_evaluation_not_actionable")
                approved = Decimal("0")
        decision_type = assessment.decision
        if reasons and decision_type not in {
            TradeDecisionType.ABSTAIN,
            TradeDecisionType.REJECTED,
        }:
            decision_type = TradeDecisionType.REJECTED
            approved = Decimal("0")
        decision = self._decision(
            portfolio=portfolio,
            context=context,
            decision_type=decision_type,
            decided_at=decided_at,
            proposed=proposed,
            approved=approved,
            reasons=tuple(dict.fromkeys(reasons)),
            checks=tuple(dict.fromkeys(checks)),
            correlation_id=correlation_id,
            causation_id=causation_id,
            side=side,
            decision_source=decision_source,
            override_reason=override_reason,
            idempotency_key=idempotency_key,
        )
        await repository.add_decision(decision)
        if decision_type in {
            TradeDecisionType.ABSTAIN,
            TradeDecisionType.REJECTED,
        }:
            order = None
            if side is not None and proposed > 0:
                order = PaperOrder(
                    order_id=self._id_factory(),
                    decision_id=decision.decision_id,
                    portfolio_id=portfolio.portfolio_id,
                    prediction_run_id=context.prediction_run_id,
                    market_id=context.market_id,
                    side=side,
                    requested_at=decided_at,
                    requested_stake=proposed,
                    status=PaperOrderStatus.REJECTED,
                    rejection_reason=",".join(decision.rejection_reasons),
                    configuration_hash=self.configuration_hash,
                )
                await repository.add_order(order)
            return PaperTradingOutcome(
                decision,
                order,
                None,
                None,
                evaluation,
            )
        assert side is not None
        assert context.market_probability is not None
        execution = self._cost_model.execute(
            ExecutionContext(
                side=side,
                market_probability=context.market_probability,
                approved_stake=approved,
                liquidity=context.liquidity,
                data_age=(
                    decided_at - context.observation_at
                    if context.observation_at is not None
                    else None
                ),
            )
        )
        if execution.net_cost > portfolio.cash_balance:
            raise PaperTradingConfigurationError(
                "simulated execution exceeded approved available capital"
            )
        order = PaperOrder(
            order_id=self._id_factory(),
            decision_id=decision.decision_id,
            portfolio_id=portfolio.portfolio_id,
            prediction_run_id=context.prediction_run_id,
            market_id=context.market_id,
            side=side,
            requested_at=decided_at,
            requested_stake=approved,
            status=PaperOrderStatus.FILLED,
            rejection_reason=None,
            configuration_hash=self.configuration_hash,
        )
        trade_hash = canonical_sha256(
            {
                "prediction_result_hash": context.prediction_result_hash,
                "decision_result_hash": decision.result_hash,
                "executed_at": decided_at,
                "execution": execution,
                "configuration_hash": self.configuration_hash,
            }
        )
        trade = PaperTrade(
            trade_id=self._id_factory(),
            order_id=order.order_id,
            executed_at=decided_at,
            side=execution.side,
            entry_probability=execution.entry_probability,
            effective_probability=execution.effective_probability,
            units=execution.units,
            gross_cost=execution.gross_cost,
            fees=execution.fees,
            slippage_cost=execution.slippage_cost,
            net_cost=execution.net_cost,
            maximum_loss=execution.maximum_loss,
            potential_payout=execution.potential_payout,
            execution_model=execution.execution_model,
            result_hash=trade_hash,
        )
        position = PaperPosition(
            position_id=self._id_factory(),
            portfolio_id=portfolio.portfolio_id,
            market_id=context.market_id,
            category=context.category,
            side=side,
            opened_at=decided_at,
            closed_at=None,
            status=PaperPositionStatus.OPEN,
            units=trade.units,
            average_entry_probability=trade.effective_probability,
            invested_amount=trade.net_cost,
            current_mark_probability=context.market_probability,
            unrealized_pnl=trade.gross_cost - trade.net_cost,
            realized_pnl=Decimal("0"),
            settlement_outcome=None,
            prediction_run_id=context.prediction_run_id,
            trade_id=trade.trade_id,
            opportunity_level=context.opportunity_level.value,
            entry_edge=context.edge or Decimal("0"),
            entry_confidence=context.confidence,
        )
        updated_portfolio = portfolio.open_position(
            net_cost=trade.net_cost,
            initial_mark_value=trade.gross_cost,
            occurred_at=decided_at,
        )
        await repository.add_order(order)
        await repository.add_trade(trade)
        await repository.add_position(position)
        await repository.update_portfolio(updated_portfolio)
        await repository.add_ledger_entry(
            PaperLedgerEntry(
                ledger_entry_id=self._id_factory(),
                portfolio_id=portfolio.portfolio_id,
                entry_type=LedgerEntryType.POSITION_OPENED,
                occurred_at=decided_at,
                amount=-trade.net_cost,
                cash_balance_after=updated_portfolio.cash_balance,
                reserved_balance_after=updated_portfolio.reserved_balance,
                equity_after=updated_portfolio.equity,
                reference_type="paper_trade",
                reference_id=trade.trade_id,
                result_hash=canonical_sha256(
                    {
                        "type": LedgerEntryType.POSITION_OPENED,
                        "trade_result_hash": trade.result_hash,
                        "amount": -trade.net_cost,
                        "cash_after": updated_portfolio.cash_balance,
                        "reserved_after": updated_portfolio.reserved_balance,
                    }
                ),
            )
        )
        return PaperTradingOutcome(
            decision,
            order,
            trade,
            position,
            evaluation,
        )

    def _decision(
        self,
        *,
        portfolio: PaperPortfolio,
        context: TradingPredictionContext,
        decision_type: TradeDecisionType,
        decided_at: datetime,
        proposed: Decimal,
        approved: Decimal,
        reasons: tuple[str, ...],
        checks: tuple[str, ...],
        correlation_id: str,
        causation_id: str | None,
        side: PositionSide | None,
        decision_source: TradeDecisionSource,
        override_reason: str | None,
        idempotency_key: str | None,
    ) -> TradeDecision:
        result_hash = canonical_sha256(
            {
                "prediction_result_hash": context.prediction_result_hash,
                "portfolio_configuration_hash": portfolio.strategy_configuration_hash,
                "decided_at": decided_at,
                "decision": decision_type,
                "side": side,
                "market_probability": context.market_probability,
                "system_probability": context.system_probability,
                "edge": context.edge,
                "confidence": context.confidence,
                "opportunity_level": context.opportunity_level,
                "proposed_stake": proposed,
                "approved_stake": approved,
                "rejection_reasons": reasons,
                "risk_checks": checks,
                "decision_source": decision_source,
                "override_reason": override_reason,
                "idempotency_key": idempotency_key,
            }
        )
        return TradeDecision(
            decision_id=self._id_factory(),
            prediction_run_id=context.prediction_run_id,
            portfolio_id=portfolio.portfolio_id,
            decided_at=decided_at,
            decision=decision_type,
            market_probability=context.market_probability,
            system_probability=context.system_probability,
            edge=context.edge,
            confidence=context.confidence,
            opportunity_level=context.opportunity_level.value,
            proposed_stake=proposed,
            approved_stake=approved,
            rejection_reasons=reasons,
            risk_checks=checks,
            configuration_hash=self.configuration_hash,
            result_hash=result_hash,
            correlation_id=correlation_id,
            causation_id=causation_id,
            experiment_run_id=context.experiment_run_id,
            side=side,
            decision_source=decision_source,
            override_reason=override_reason,
            idempotency_key=idempotency_key,
        )

    def _settlement(
        self,
        *,
        position: PaperPosition,
        outcome: ResolutionOutcome,
        resolved_at: datetime,
        created_at: datetime,
        correlation_id: str,
        causation_id: str | None,
    ) -> PaperSettlement:
        if outcome is ResolutionOutcome.CANCELLED:
            gross_payout = position.invested_amount
            policy = self._cancelled_settlement_policy
        else:
            won = (position.side is PositionSide.YES and outcome is ResolutionOutcome.YES) or (
                position.side is PositionSide.NO and outcome is ResolutionOutcome.NO
            )
            gross_payout = position.units if won else Decimal("0")
            policy = "official_binary_outcome"
        fees = Decimal("0")
        net_payout = gross_payout - fees
        realized_pnl = (
            Decimal("0")
            if outcome is ResolutionOutcome.CANCELLED
            else net_payout - position.invested_amount
        )
        result_hash = canonical_sha256(
            {
                "position": {
                    "market_id": position.market_id,
                    "side": position.side,
                    "opened_at": position.opened_at,
                    "units": position.units,
                    "invested_amount": position.invested_amount,
                },
                "resolved_at": resolved_at,
                "outcome": outcome,
                "gross_payout": gross_payout,
                "fees": fees,
                "net_payout": net_payout,
                "realized_pnl": realized_pnl,
                "settlement_policy": policy,
            }
        )
        return PaperSettlement(
            settlement_id=self._id_factory(),
            position_id=position.position_id,
            market_id=position.market_id,
            resolved_at=resolved_at,
            outcome=outcome.value,
            gross_payout=gross_payout,
            fees=fees,
            net_payout=net_payout,
            realized_pnl=realized_pnl,
            settlement_policy=policy,
            result_hash=result_hash,
            created_at=created_at,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

    def _settlement_ledger(
        self,
        *,
        portfolio: PaperPortfolio,
        settlement: PaperSettlement,
    ) -> PaperLedgerEntry:
        entry_type = (
            LedgerEntryType.CANCELLATION_REFUND
            if settlement.outcome == ResolutionOutcome.CANCELLED.value
            else LedgerEntryType.SETTLEMENT
        )
        return PaperLedgerEntry(
            ledger_entry_id=self._id_factory(),
            portfolio_id=portfolio.portfolio_id,
            entry_type=entry_type,
            occurred_at=settlement.created_at,
            amount=settlement.net_payout,
            cash_balance_after=portfolio.cash_balance,
            reserved_balance_after=portfolio.reserved_balance,
            equity_after=portfolio.equity,
            reference_type="paper_settlement",
            reference_id=settlement.settlement_id,
            result_hash=canonical_sha256(
                {
                    "type": entry_type,
                    "settlement_result_hash": settlement.result_hash,
                    "amount": settlement.net_payout,
                    "cash_after": portfolio.cash_balance,
                    "reserved_after": portfolio.reserved_balance,
                }
            ),
        )

    async def _performance_snapshot(
        self,
        *,
        repository: PaperTradingRepository,
        portfolio: PaperPortfolio,
        recorded_at: datetime,
    ) -> PaperPerformanceSnapshot:
        open_count, closed_count, _ = await repository.performance_counters(portfolio.portfolio_id)
        cumulative_costs = await repository.cumulative_costs(portfolio.portfolio_id)
        previous_peak = await repository.maximum_equity(portfolio.portfolio_id)
        peak = max(previous_peak, portfolio.initial_balance, portfolio.equity)
        drawdown = (peak - portfolio.equity) / peak if peak > 0 else Decimal("0")
        result_hash = canonical_sha256(
            {
                "recorded_at": recorded_at,
                "currency_unit": portfolio.currency_unit,
                "cash_balance": portfolio.cash_balance,
                "reserved_balance": portfolio.reserved_balance,
                "realized_pnl": portfolio.realized_pnl,
                "unrealized_pnl": portfolio.unrealized_pnl,
                "equity": portfolio.equity,
                "total_exposure": portfolio.total_exposure,
                "cumulative_costs": cumulative_costs,
                "drawdown": drawdown,
                "open_positions": open_count,
                "closed_positions": closed_count,
                "configuration_hash": self.configuration_hash,
            }
        )
        return await repository.add_performance_snapshot(
            PaperPerformanceSnapshot(
                snapshot_id=self._id_factory(),
                portfolio_id=portfolio.portfolio_id,
                recorded_at=recorded_at,
                cash_balance=portfolio.cash_balance,
                reserved_balance=portfolio.reserved_balance,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl,
                equity=portfolio.equity,
                total_exposure=portfolio.total_exposure,
                cumulative_costs=cumulative_costs,
                drawdown=drawdown,
                open_positions=open_count,
                closed_positions=closed_count,
                configuration_hash=self.configuration_hash,
                result_hash=result_hash,
            )
        )

    def _resolved_configuration(self) -> Mapping[str, object]:
        entry_configuration = getattr(self._entry_policy, "configuration", None)
        cost_configuration = getattr(self._cost_model, "configuration", None)
        return {
            "strategy": "ai_polyphite_threshold_v1",
            "entry_policy": {
                "name": self._entry_policy.name,
                "version": self._entry_policy.version,
                "configuration": (
                    asdict(entry_configuration) if entry_configuration is not None else {}
                ),
            },
            "sizing_policy": {
                "name": self._sizing_policy.name,
                "version": self._sizing_policy.version,
                "configuration": asdict(self._sizing_policy.configuration),
            },
            "risk_policy": {
                "name": self._risk_policy.name,
                "version": self._risk_policy.version,
            },
            "cost_model": {
                "name": self._cost_model.name,
                "version": self._cost_model.version,
                "configuration": (
                    asdict(cost_configuration) if cost_configuration is not None else {}
                ),
            },
            "cancelled_settlement_policy": self._cancelled_settlement_policy,
            "execution": "simulated_binary_probability_contract",
            "real_money": False,
        }


class PaperSettlementService:
    """Explicit settlement façade kept separate from entry policy decisions."""

    def __init__(self, orchestrator: PaperTradingOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def settle(
        self,
        command: SettlePaperPortfolio,
    ) -> SettlementBatchResult:
        return await self._orchestrator.settle(command)


def _assert_experiment_compatibility(
    portfolio: PaperPortfolio,
    context: TradingPredictionContext,
) -> None:
    if portfolio.experiment_run_id != context.experiment_run_id:
        raise PaperTradingConfigurationError(
            "portfolio and prediction belong to incompatible experiments"
        )
    if portfolio.status is not PaperPortfolioStatus.ACTIVE:
        raise PaperTradingConfigurationError("portfolio is not active")


def _assert_compatible_portfolio(
    portfolio: PaperPortfolio,
    command: CreatePaperPortfolio,
) -> None:
    if (
        portfolio.currency_unit is not command.currency_unit
        or portfolio.initial_balance != command.initial_balance
        or portfolio.name != command.name
    ):
        raise PaperTradingIdempotencyConflictError(
            "experiment portfolio already exists with different configuration"
        )


def _assert_compatible_manual_override(
    outcome: PaperTradingOutcome,
    command: RunManualPaperTrade,
) -> None:
    decision = outcome.decision
    if (
        decision.decision_source is not TradeDecisionSource.MANUAL_OVERRIDE
        or decision.prediction_run_id != command.prediction_run_id
        or decision.portfolio_id != command.portfolio_id
        or decision.side is not command.side
        or decision.proposed_stake != command.requested_stake
        or decision.override_reason != command.override_reason.strip()
        or decision.idempotency_key != command.idempotency_key.strip()
    ):
        raise PaperTradingIdempotencyConflictError(
            "manual override idempotency scope contains different input"
        )
