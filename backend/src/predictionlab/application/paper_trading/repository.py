"""Persistence ports for transactional paper trading and read queries."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, Self
from uuid import UUID

from predictionlab.application.paper_trading.models import (
    EquityCurvePoint,
    ListPaperPortfolios,
    ListPaperPositions,
    ListPaperSettlements,
    ListPaperTrades,
    ListTradeDecisions,
    OpenPositionContext,
    PaperPage,
    PaperPerformanceData,
    PaperPortfolioDetail,
    PaperPositionDetail,
    PaperSettlementDetail,
    PaperTradeDetail,
    PaperTradingOutcome,
    PortfolioExposure,
    TradeDecisionDetail,
    TradingPredictionContext,
)
from predictionlab.domain.paper_trading import (
    PaperLedgerEntry,
    PaperOrder,
    PaperPerformanceSnapshot,
    PaperPortfolio,
    PaperPosition,
    PaperSettlement,
    PaperTrade,
    TradeDecision,
)


class PaperTradingRepository(Protocol):
    async def get_portfolio(
        self,
        portfolio_id: UUID,
        *,
        for_update: bool = False,
    ) -> PaperPortfolio | None: ...

    async def find_experiment_portfolio(
        self,
        *,
        experiment_run_id: UUID,
        strategy_configuration_hash: str,
    ) -> PaperPortfolio | None: ...

    async def add_portfolio(self, portfolio: PaperPortfolio) -> None: ...

    async def update_portfolio(self, portfolio: PaperPortfolio) -> None: ...

    async def prediction_context(
        self,
        prediction_run_id: UUID,
    ) -> TradingPredictionContext | None: ...

    async def find_outcome(
        self,
        *,
        portfolio_id: UUID,
        prediction_run_id: UUID,
    ) -> PaperTradingOutcome | None: ...

    async def exposure(
        self,
        *,
        portfolio_id: UUID,
        market_id: UUID,
        category: str | None,
    ) -> PortfolioExposure: ...

    async def add_decision(self, decision: TradeDecision) -> None: ...

    async def add_order(self, order: PaperOrder) -> None: ...

    async def add_trade(self, trade: PaperTrade) -> None: ...

    async def add_position(self, position: PaperPosition) -> None: ...

    async def update_position(self, position: PaperPosition) -> None: ...

    async def add_settlement(self, settlement: PaperSettlement) -> None: ...

    async def add_ledger_entry(self, entry: PaperLedgerEntry) -> None: ...

    async def add_performance_snapshot(
        self,
        snapshot: PaperPerformanceSnapshot,
    ) -> PaperPerformanceSnapshot: ...

    async def open_positions(
        self,
        *,
        portfolio_id: UUID,
        as_of: datetime,
    ) -> tuple[OpenPositionContext, ...]: ...

    async def performance_counters(
        self,
        portfolio_id: UUID,
    ) -> tuple[int, int, int]: ...

    async def cumulative_costs(self, portfolio_id: UUID) -> Decimal: ...

    async def maximum_equity(self, portfolio_id: UUID) -> Decimal: ...


class PaperTradingUnitOfWork(Protocol):
    paper_trading: PaperTradingRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class PaperTradingReadRepository(Protocol):
    async def list_portfolios(
        self,
        query: ListPaperPortfolios,
    ) -> PaperPage[PaperPortfolioDetail]: ...

    async def get_portfolio(self, portfolio_id: UUID) -> PaperPortfolioDetail | None: ...

    async def list_decisions(
        self,
        query: ListTradeDecisions,
    ) -> PaperPage[TradeDecisionDetail]: ...

    async def list_trades(
        self,
        query: ListPaperTrades,
    ) -> PaperPage[PaperTradeDetail]: ...

    async def get_trade(self, trade_id: UUID) -> PaperTradeDetail | None: ...

    async def list_positions(
        self,
        query: ListPaperPositions,
    ) -> PaperPage[PaperPositionDetail]: ...

    async def get_position(self, position_id: UUID) -> PaperPositionDetail | None: ...

    async def list_settlements(
        self,
        query: ListPaperSettlements,
    ) -> PaperPage[PaperSettlementDetail]: ...

    async def equity_curve(self, portfolio_id: UUID) -> tuple[EquityCurvePoint, ...]: ...

    async def performance_data(
        self,
        portfolio_id: UUID,
    ) -> PaperPerformanceData | None: ...
