"""Read-only paper trading queries and transparent performance evaluation."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from predictionlab.application.paper_trading.models import (
    EquityCurvePoint,
    ListPaperPortfolios,
    ListPaperPositions,
    ListPaperSettlements,
    ListPaperTrades,
    ListTradeDecisions,
    PaperPage,
    PaperPerformanceData,
    PaperPerformanceReport,
    PaperPortfolioDetail,
    PaperPositionDetail,
    PaperSettlementDetail,
    PaperTradeDetail,
    SimulationAlert,
    TradeDecisionDetail,
)
from predictionlab.application.paper_trading.repository import (
    PaperTradingReadRepository,
)
from predictionlab.domain.paper_trading import (
    ConservativeCostModel,
    ExecutionCostModel,
    FixedThresholdBaseline,
    MarketFollowBaseline,
    NoTradeBaseline,
    PaperPerformanceMetrics,
    evaluate_baseline,
    evaluate_performance,
)


class PaperTradingNotFoundError(Exception):
    pass


class PaperTradingQueryService:
    def __init__(self, repository: PaperTradingReadRepository) -> None:
        self._repository = repository

    async def list_portfolios(
        self,
        query: ListPaperPortfolios,
    ) -> PaperPage[PaperPortfolioDetail]:
        return await self._repository.list_portfolios(query)

    async def get_portfolio(self, portfolio_id: UUID) -> PaperPortfolioDetail:
        value = await self._repository.get_portfolio(portfolio_id)
        if value is None:
            raise PaperTradingNotFoundError(str(portfolio_id))
        return value

    async def list_decisions(
        self,
        query: ListTradeDecisions,
    ) -> PaperPage[TradeDecisionDetail]:
        return await self._repository.list_decisions(query)

    async def list_trades(
        self,
        query: ListPaperTrades,
    ) -> PaperPage[PaperTradeDetail]:
        return await self._repository.list_trades(query)

    async def get_trade(self, trade_id: UUID) -> PaperTradeDetail:
        value = await self._repository.get_trade(trade_id)
        if value is None:
            raise PaperTradingNotFoundError(str(trade_id))
        return value

    async def list_positions(
        self,
        query: ListPaperPositions,
    ) -> PaperPage[PaperPositionDetail]:
        return await self._repository.list_positions(query)

    async def get_position(self, position_id: UUID) -> PaperPositionDetail:
        value = await self._repository.get_position(position_id)
        if value is None:
            raise PaperTradingNotFoundError(str(position_id))
        return value

    async def list_settlements(
        self,
        query: ListPaperSettlements,
    ) -> PaperPage[PaperSettlementDetail]:
        return await self._repository.list_settlements(query)

    async def equity_curve(self, portfolio_id: UUID) -> tuple[EquityCurvePoint, ...]:
        if await self._repository.get_portfolio(portfolio_id) is None:
            raise PaperTradingNotFoundError(str(portfolio_id))
        return await self._repository.equity_curve(portfolio_id)


class PaperPerformanceService:
    def __init__(
        self,
        repository: PaperTradingReadRepository,
        *,
        preliminary_threshold: int = 10,
        observation_threshold: int = 30,
        expansion_threshold: int = 100,
        maximum_concentration: Decimal = Decimal("0.25"),
        cost_model: ExecutionCostModel | None = None,
    ) -> None:
        self._repository = repository
        self._preliminary_threshold = preliminary_threshold
        self._observation_threshold = observation_threshold
        self._expansion_threshold = expansion_threshold
        self._maximum_concentration = maximum_concentration
        self._cost_model = cost_model or ConservativeCostModel()

    async def evaluate(self, portfolio_id: UUID) -> PaperPerformanceReport:
        data = await self._repository.performance_data(portfolio_id)
        if data is None:
            raise PaperTradingNotFoundError(str(portfolio_id))
        metrics = evaluate_performance(
            initial_capital=data.portfolio.initial_balance,
            final_equity=data.portfolio.equity,
            realized_pnl=data.portfolio.realized_pnl,
            unrealized_pnl=data.portfolio.unrealized_pnl,
            decision_count=data.decision_count,
            abstention_count=data.abstention_count,
            rejection_count=data.rejection_count,
            open_trade_count=data.open_position_count,
            samples=data.samples,
            equity_curve=tuple(point.equity for point in data.equity_curve),
            exposure_curve=tuple(point.exposure for point in data.equity_curve),
            preliminary_threshold=self._preliminary_threshold,
            observation_threshold=self._observation_threshold,
            expansion_threshold=self._expansion_threshold,
            maximum_concentration=self._maximum_concentration,
        )
        stake = min(
            max(
                data.portfolio.initial_balance * Decimal("0.01"),
                Decimal("0.50"),
            ),
            Decimal("10.00"),
        )
        baselines = tuple(
            evaluate_baseline(
                baseline=baseline,
                samples=data.baseline_samples,
                market_probabilities=data.market_probabilities,
                system_probabilities=data.system_probabilities,
                outcomes=data.outcomes,
                initial_capital=data.portfolio.initial_balance,
                stake=stake,
                cost_model=self._cost_model,
            )
            for baseline in (
                NoTradeBaseline(),
                MarketFollowBaseline(),
                FixedThresholdBaseline(),
            )
        )
        return PaperPerformanceReport(
            portfolio=data.portfolio,
            metrics=metrics,
            baselines=baselines,
            alerts=_alerts(
                data=data,
                metrics=metrics,
                minimum_closed=self._preliminary_threshold,
            ),
            strategy_configuration_hash=data.portfolio.strategy_configuration_hash,
        )


def _alerts(
    *,
    data: PaperPerformanceData,
    metrics: PaperPerformanceMetrics,
    minimum_closed: int,
) -> tuple[SimulationAlert, ...]:
    alerts: list[SimulationAlert] = []
    exposure_ratio = (
        data.portfolio.total_exposure / data.portfolio.equity
        if data.portfolio.equity > 0
        else Decimal("0")
    )
    if exposure_ratio >= Decimal("0.40"):
        alerts.append(_alert("high_exposure", "warning"))
    if data.maximum_category_concentration >= Decimal("0.15"):
        alerts.append(_alert("category_concentration", "warning"))
    if metrics.maximum_drawdown >= Decimal("0.20"):
        alerts.append(_alert("drawdown_limit", "error"))
    if data.consecutive_losses >= 3:
        alerts.append(_alert("consecutive_losses", "warning"))
    if data.rejection_count:
        alerts.append(_alert("rejected_trade", "info"))
    if data.unsettled_resolved_count:
        alerts.append(_alert("unsettled_resolution", "error"))
    if data.other_pending_count:
        alerts.append(_alert("other_outcome_pending", "warning"))
    if metrics.total_costs > data.portfolio.initial_balance * Decimal("0.02"):
        alerts.append(_alert("excessive_costs", "warning"))
    if data.stale_open_count:
        alerts.append(_alert("stale_data", "warning"))
    if metrics.closed_trade_count < minimum_closed:
        alerts.append(_alert("insufficient_closed_trades", "info"))
    return tuple(alerts)


def _alert(code: str, severity: str) -> SimulationAlert:
    return SimulationAlert(code=code, severity=severity, message=code)
