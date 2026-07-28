"""Read-only paper trading API and guarded development simulation controls."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from predictionlab.application.paper_trading import (
    CreatePaperPortfolio,
    EquityCurvePoint,
    ListPaperPortfolios,
    ListPaperPositions,
    ListPaperSettlements,
    ListPaperTrades,
    ListTradeDecisions,
    PaperPage,
    PaperPerformanceReport,
    PaperPerformanceService,
    PaperPortfolioDetail,
    PaperPortfolioNotFoundError,
    PaperPositionDetail,
    PaperSettlementDetail,
    PaperTradeDetail,
    PaperTradingConfigurationError,
    PaperTradingIdempotencyConflictError,
    PaperTradingNotFoundError,
    PaperTradingOrchestrator,
    PaperTradingQueryService,
    PredictionRunNotFoundError,
    SettlePaperPortfolio,
    TradeDecisionDetail,
)
from predictionlab.core.context import get_correlation_id
from predictionlab.core.settings import AppEnvironment
from predictionlab.domain.markets import ResolutionOutcome
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolioStatus,
    PaperPositionStatus,
    PositionSide,
    SampleEvidenceState,
    TradeDecisionType,
)
from predictionlab.domain.predictions import OpportunityLevel

router = APIRouter(tags=["paper trading"])


class PaperPortfolioResponse(BaseModel):
    portfolio_id: UUID
    name: str
    currency_unit: CurrencyUnit
    initial_balance: Decimal
    cash_balance: Decimal
    reserved_balance: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    total_exposure: Decimal
    status: PaperPortfolioStatus
    strategy_configuration_hash: str
    experiment_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    simulation_only: bool = True


class PaperPortfolioPageResponse(BaseModel):
    items: list[PaperPortfolioResponse]
    page: int
    page_size: int
    total: int
    pages: int


class TradeDecisionResponse(BaseModel):
    decision_id: UUID
    prediction_run_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    decided_at: datetime
    decision: TradeDecisionType
    side: PositionSide | None
    market_probability: Decimal | None
    system_probability: Decimal | None
    edge: Decimal | None
    confidence: Decimal
    opportunity_level: OpportunityLevel
    proposed_stake: Decimal
    approved_stake: Decimal
    rejection_reasons: list[str]
    risk_checks: list[str]
    configuration_hash: str
    result_hash: str
    correlation_id: str
    causation_id: str | None
    experiment_run_id: UUID | None
    prediction_result_hash: str
    simulation_only: bool = True


class TradeDecisionPageResponse(BaseModel):
    items: list[TradeDecisionResponse]
    page: int
    page_size: int
    total: int
    pages: int


class PaperTradeResponse(BaseModel):
    trade_id: UUID
    order_id: UUID
    decision_id: UUID
    portfolio_id: UUID
    prediction_run_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    executed_at: datetime
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
    result_hash: str
    decision_reasons: list[str]
    prediction_result_hash: str
    experiment_run_id: UUID | None
    simulation_only: bool = True
    probability_is_informative: bool = True


class PaperTradePageResponse(BaseModel):
    items: list[PaperTradeResponse]
    page: int
    page_size: int
    total: int
    pages: int


class PaperPositionResponse(BaseModel):
    position_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    category: str | None
    side: PositionSide
    opened_at: datetime
    closed_at: datetime | None
    status: PaperPositionStatus
    units: Decimal
    average_entry_probability: Decimal
    invested_amount: Decimal
    current_mark_probability: Decimal | None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    settlement_outcome: ResolutionOutcome | None
    prediction_run_id: UUID
    trade_id: UUID
    opportunity_level: OpportunityLevel
    entry_edge: Decimal
    entry_confidence: Decimal
    experiment_run_id: UUID | None
    simulation_only: bool = True
    mark_is_informative: bool = True


class PaperPositionPageResponse(BaseModel):
    items: list[PaperPositionResponse]
    page: int
    page_size: int
    total: int
    pages: int


class PaperSettlementResponse(BaseModel):
    settlement_id: UUID
    position_id: UUID
    portfolio_id: UUID
    market_id: UUID
    market_title: str
    resolved_at: datetime
    outcome: ResolutionOutcome
    gross_payout: Decimal
    fees: Decimal
    net_payout: Decimal
    realized_pnl: Decimal
    settlement_policy: str
    result_hash: str
    created_at: datetime
    correlation_id: str
    causation_id: str | None
    experiment_run_id: UUID | None
    simulation_only: bool = True


class PaperSettlementPageResponse(BaseModel):
    items: list[PaperSettlementResponse]
    page: int
    page_size: int
    total: int
    pages: int


class EquityCurvePointResponse(BaseModel):
    recorded_at: datetime
    equity: Decimal
    drawdown: Decimal
    exposure: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    cumulative_costs: Decimal
    result_hash: str
    valuation_is_simulated: bool = True


class StrategyBreakdownResponse(BaseModel):
    key: str
    trade_count: int
    net_pnl: Decimal


class BaselinePerformanceResponse(BaseModel):
    name: str
    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    simulated_roi: Decimal
    trade_count: int
    total_costs: Decimal


class SimulationAlertResponse(BaseModel):
    code: str
    severity: str
    message: str


class PaperMetricsResponse(BaseModel):
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
    by_category: list[StrategyBreakdownResponse]
    by_opportunity_level: list[StrategyBreakdownResponse]
    by_edge_range: list[StrategyBreakdownResponse]
    by_confidence_range: list[StrategyBreakdownResponse]


class PaperPerformanceResponse(BaseModel):
    portfolio: PaperPortfolioResponse
    metrics: PaperMetricsResponse
    baselines: list[BaselinePerformanceResponse]
    alerts: list[SimulationAlertResponse]
    strategy_configuration_hash: str
    simulation_only: bool
    disclaimer: str = (
        "Simulated research results. They do not represent real money or guarantee future returns."
    )


class CreatePaperPortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    currency_unit: CurrencyUnit = CurrencyUnit.USD_SIMULATED
    initial_balance: Decimal = Field(default=Decimal("100"), gt=0)
    experiment_run_id: UUID | None = None
    causation_id: str | None = Field(default=None, min_length=1, max_length=200)


class RunPaperTradingRequest(BaseModel):
    portfolio_id: UUID
    prediction_run_id: UUID | None = None
    prediction_run_ids: list[UUID] = Field(default_factory=list, max_length=100)
    causation_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_predictions(self) -> RunPaperTradingRequest:
        values = [
            *(self.prediction_run_ids),
            *([self.prediction_run_id] if self.prediction_run_id is not None else []),
        ]
        if not values:
            raise ValueError("at least one prediction_run_id is required")
        if len(set(values)) != len(values):
            raise ValueError("prediction_run_ids must be unique")
        return self

    @property
    def all_prediction_ids(self) -> tuple[UUID, ...]:
        return (
            *([self.prediction_run_id] if self.prediction_run_id is not None else []),
            *self.prediction_run_ids,
        )


class ManualPaperRunResponse(BaseModel):
    decision_ids: list[UUID]
    trade_ids: list[UUID]
    position_ids: list[UUID]
    result_hashes: list[str]
    simulation_only: bool = True


class SettlePaperTradingRequest(BaseModel):
    portfolio_id: UUID
    settled_at: datetime | None = None
    causation_id: str | None = Field(default=None, min_length=1, max_length=200)


class ManualSettlementResponse(BaseModel):
    settlement_ids: list[UUID]
    equity: Decimal
    result_hash: str
    simulation_only: bool = True


def get_paper_query_service(request: Request) -> PaperTradingQueryService:
    return cast(PaperTradingQueryService, request.app.state.paper_trading_query_service)


def get_paper_performance_service(request: Request) -> PaperPerformanceService:
    return cast(PaperPerformanceService, request.app.state.paper_performance_service)


def get_paper_orchestrator(request: Request) -> PaperTradingOrchestrator:
    return cast(PaperTradingOrchestrator, request.app.state.paper_trading_orchestrator)


@router.get(
    "/paper-portfolios",
    response_model=PaperPortfolioPageResponse,
    summary="List virtual research portfolios",
    operation_id="list_paper_portfolios",
)
async def list_paper_portfolios(
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    portfolio_status: Annotated[
        PaperPortfolioStatus | None,
        Query(alias="status"),
    ] = None,
    experiment_run_id: UUID | None = None,
    currency_unit: CurrencyUnit | None = None,
) -> PaperPortfolioPageResponse:
    result = await service.list_portfolios(
        ListPaperPortfolios(
            page=page,
            page_size=page_size,
            status=portfolio_status,
            experiment_run_id=experiment_run_id,
            currency_unit=currency_unit,
        )
    )
    return _portfolio_page(result)


@router.get(
    "/paper-portfolios/{portfolio_id}",
    response_model=PaperPortfolioResponse,
    summary="Get one virtual portfolio",
    operation_id="get_paper_portfolio",
)
async def get_paper_portfolio(
    portfolio_id: UUID,
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
) -> PaperPortfolioResponse:
    try:
        return _portfolio(await service.get_portfolio(portfolio_id))
    except PaperTradingNotFoundError as exc:
        raise _not_found() from exc


@router.get(
    "/paper-portfolios/{portfolio_id}/performance",
    response_model=PaperPerformanceResponse,
    summary="Evaluate simulated strategy performance",
    operation_id="get_paper_portfolio_performance",
)
async def get_paper_portfolio_performance(
    portfolio_id: UUID,
    service: Annotated[PaperPerformanceService, Depends(get_paper_performance_service)],
) -> PaperPerformanceResponse:
    try:
        return _performance(await service.evaluate(portfolio_id))
    except PaperTradingNotFoundError as exc:
        raise _not_found() from exc


@router.get(
    "/paper-portfolios/{portfolio_id}/equity-curve",
    response_model=list[EquityCurvePointResponse],
    summary="Get simulated equity and drawdown history",
    operation_id="get_paper_portfolio_equity_curve",
)
async def get_paper_portfolio_equity_curve(
    portfolio_id: UUID,
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
) -> list[EquityCurvePointResponse]:
    try:
        return [_equity_point(item) for item in await service.equity_curve(portfolio_id)]
    except PaperTradingNotFoundError as exc:
        raise _not_found() from exc


@router.get(
    "/paper-trades",
    response_model=PaperTradePageResponse,
    summary="List deterministic simulated fills",
    operation_id="list_paper_trades",
)
async def list_paper_trades(
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    portfolio_id: UUID | None = None,
    market_id: UUID | None = None,
    category: str | None = None,
    side: PositionSide | None = None,
    experiment_run_id: UUID | None = None,
    executed_from: Annotated[datetime | None, Query(alias="from")] = None,
    executed_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> PaperTradePageResponse:
    result = await service.list_trades(
        ListPaperTrades(
            page=page,
            page_size=page_size,
            portfolio_id=portfolio_id,
            market_id=market_id,
            category=category,
            side=side,
            experiment_run_id=experiment_run_id,
            executed_from=executed_from,
            executed_to=executed_to,
        )
    )
    return _trade_page(result)


@router.get(
    "/paper-trades/{trade_id}",
    response_model=PaperTradeResponse,
    summary="Get one simulated fill and its provenance",
    operation_id="get_paper_trade",
)
async def get_paper_trade(
    trade_id: UUID,
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
) -> PaperTradeResponse:
    try:
        return _trade(await service.get_trade(trade_id))
    except PaperTradingNotFoundError as exc:
        raise _not_found() from exc


@router.get(
    "/paper-positions",
    response_model=PaperPositionPageResponse,
    summary="List open and settled virtual positions",
    operation_id="list_paper_positions",
)
async def list_paper_positions(
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    portfolio_id: UUID | None = None,
    market_id: UUID | None = None,
    category: str | None = None,
    side: PositionSide | None = None,
    position_status: Annotated[
        PaperPositionStatus | None,
        Query(alias="status"),
    ] = None,
    experiment_run_id: UUID | None = None,
) -> PaperPositionPageResponse:
    result = await service.list_positions(
        ListPaperPositions(
            page=page,
            page_size=page_size,
            portfolio_id=portfolio_id,
            market_id=market_id,
            category=category,
            side=side,
            status=position_status,
            experiment_run_id=experiment_run_id,
        )
    )
    return _position_page(result)


@router.get(
    "/paper-positions/{position_id}",
    response_model=PaperPositionResponse,
    summary="Get one virtual position",
    operation_id="get_paper_position",
)
async def get_paper_position(
    position_id: UUID,
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
) -> PaperPositionResponse:
    try:
        return _position(await service.get_position(position_id))
    except PaperTradingNotFoundError as exc:
        raise _not_found() from exc


@router.get(
    "/trade-decisions",
    response_model=TradeDecisionPageResponse,
    summary="List approvals, abstentions and risk rejections",
    operation_id="list_trade_decisions",
)
async def list_trade_decisions(
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    portfolio_id: UUID | None = None,
    market_id: UUID | None = None,
    category: str | None = None,
    side: PositionSide | None = None,
    decision: TradeDecisionType | None = None,
    opportunity_level: OpportunityLevel | None = None,
    experiment_run_id: UUID | None = None,
    decided_from: Annotated[datetime | None, Query(alias="from")] = None,
    decided_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> TradeDecisionPageResponse:
    result = await service.list_decisions(
        ListTradeDecisions(
            page=page,
            page_size=page_size,
            portfolio_id=portfolio_id,
            market_id=market_id,
            category=category,
            side=side,
            decision=decision,
            opportunity_level=opportunity_level,
            experiment_run_id=experiment_run_id,
            decided_from=decided_from,
            decided_to=decided_to,
        )
    )
    return _decision_page(result)


@router.get(
    "/paper-settlements",
    response_model=PaperSettlementPageResponse,
    summary="List official-outcome virtual settlements",
    operation_id="list_paper_settlements",
)
async def list_paper_settlements(
    service: Annotated[PaperTradingQueryService, Depends(get_paper_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    portfolio_id: UUID | None = None,
    market_id: UUID | None = None,
    outcome: ResolutionOutcome | None = None,
    experiment_run_id: UUID | None = None,
    resolved_from: Annotated[datetime | None, Query(alias="from")] = None,
    resolved_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> PaperSettlementPageResponse:
    result = await service.list_settlements(
        ListPaperSettlements(
            page=page,
            page_size=page_size,
            portfolio_id=portfolio_id,
            market_id=market_id,
            outcome=outcome,
            experiment_run_id=experiment_run_id,
            resolved_from=resolved_from,
            resolved_to=resolved_to,
        )
    )
    return _settlement_page(result)


@router.get(
    "/experiment-runs/{experiment_id}/paper-performance",
    response_model=PaperPerformanceResponse,
    summary="Evaluate the experiment's simulated portfolio",
    operation_id="get_experiment_paper_performance",
)
async def get_experiment_paper_performance(
    experiment_id: UUID,
    query_service: Annotated[
        PaperTradingQueryService,
        Depends(get_paper_query_service),
    ],
    performance_service: Annotated[
        PaperPerformanceService,
        Depends(get_paper_performance_service),
    ],
) -> PaperPerformanceResponse:
    portfolios = await query_service.list_portfolios(
        ListPaperPortfolios(experiment_run_id=experiment_id, page_size=100)
    )
    if not portfolios.items:
        raise _not_found()
    return _performance(await performance_service.evaluate(portfolios.items[0].portfolio_id))


@router.post(
    "/paper-portfolios",
    response_model=PaperPortfolioResponse,
    summary="Create a development-only virtual portfolio",
    operation_id="create_paper_portfolio_manually",
)
async def create_paper_portfolio_manually(
    payload: CreatePaperPortfolioRequest,
    request: Request,
    orchestrator: Annotated[
        PaperTradingOrchestrator,
        Depends(get_paper_orchestrator),
    ],
    query_service: Annotated[
        PaperTradingQueryService,
        Depends(get_paper_query_service),
    ],
) -> PaperPortfolioResponse:
    _require_manual_access(request)
    try:
        result = await orchestrator.create_portfolio(
            CreatePaperPortfolio(
                name=payload.name,
                currency_unit=payload.currency_unit,
                initial_balance=payload.initial_balance,
                experiment_run_id=payload.experiment_run_id,
                correlation_id=get_correlation_id(),
                causation_id=payload.causation_id,
            )
        )
    except PaperTradingIdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A portfolio with this experiment scope has different inputs.",
        ) from exc
    return _portfolio(await query_service.get_portfolio(result.portfolio.portfolio_id))


@router.post(
    "/paper-trading/run",
    response_model=ManualPaperRunResponse,
    summary="Run simulated decisions in development",
    operation_id="run_paper_trading_manually",
)
async def run_paper_trading_manually(
    payload: RunPaperTradingRequest,
    request: Request,
    orchestrator: Annotated[
        PaperTradingOrchestrator,
        Depends(get_paper_orchestrator),
    ],
) -> ManualPaperRunResponse:
    _require_manual_access(request)
    try:
        outcomes = await orchestrator.run_batch(
            portfolio_id=payload.portfolio_id,
            prediction_run_ids=payload.all_prediction_ids,
            correlation_id=get_correlation_id(),
            causation_id=payload.causation_id,
        )
    except (PaperPortfolioNotFoundError, PredictionRunNotFoundError) as exc:
        raise _not_found() from exc
    except PaperTradingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ManualPaperRunResponse(
        decision_ids=[item.decision.decision_id for item in outcomes],
        trade_ids=[item.trade.trade_id for item in outcomes if item.trade is not None],
        position_ids=[item.position.position_id for item in outcomes if item.position is not None],
        result_hashes=[value for item in outcomes for value in item.artifact_hashes],
    )


@router.post(
    "/paper-trading/settle",
    response_model=ManualSettlementResponse,
    summary="Settle visible official outcomes in development",
    operation_id="settle_paper_trading_manually",
)
async def settle_paper_trading_manually(
    payload: SettlePaperTradingRequest,
    request: Request,
    orchestrator: Annotated[
        PaperTradingOrchestrator,
        Depends(get_paper_orchestrator),
    ],
) -> ManualSettlementResponse:
    _require_manual_access(request)
    try:
        result = await orchestrator.settle(
            SettlePaperPortfolio(
                portfolio_id=payload.portfolio_id,
                settled_at=payload.settled_at or orchestrator.now(),
                correlation_id=get_correlation_id(),
                causation_id=payload.causation_id,
            )
        )
    except PaperPortfolioNotFoundError as exc:
        raise _not_found() from exc
    return ManualSettlementResponse(
        settlement_ids=[item.settlement_id for item in result.settlements],
        equity=result.performance_snapshot.equity,
        result_hash=result.performance_snapshot.result_hash,
    )


def _require_manual_access(request: Request) -> None:
    settings = request.app.state.settings
    if settings.app_env is AppEnvironment.PRODUCTION or not settings.enable_manual_paper_trading:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual paper trading controls are disabled.",
        )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Paper trading resource not found.",
    )


def _portfolio(value: PaperPortfolioDetail) -> PaperPortfolioResponse:
    return PaperPortfolioResponse(**asdict(value))


def _portfolio_page(
    value: PaperPage[PaperPortfolioDetail],
) -> PaperPortfolioPageResponse:
    return PaperPortfolioPageResponse(
        items=[_portfolio(item) for item in value.items],
        page=value.page,
        page_size=value.page_size,
        total=value.total,
        pages=value.pages,
    )


def _decision(value: TradeDecisionDetail) -> TradeDecisionResponse:
    return TradeDecisionResponse(
        **{
            **asdict(value),
            "rejection_reasons": list(value.rejection_reasons),
            "risk_checks": list(value.risk_checks),
        }
    )


def _decision_page(
    value: PaperPage[TradeDecisionDetail],
) -> TradeDecisionPageResponse:
    return TradeDecisionPageResponse(
        items=[_decision(item) for item in value.items],
        page=value.page,
        page_size=value.page_size,
        total=value.total,
        pages=value.pages,
    )


def _trade(value: PaperTradeDetail) -> PaperTradeResponse:
    return PaperTradeResponse(
        **{
            **asdict(value),
            "decision_reasons": list(value.decision_reasons),
        }
    )


def _trade_page(value: PaperPage[PaperTradeDetail]) -> PaperTradePageResponse:
    return PaperTradePageResponse(
        items=[_trade(item) for item in value.items],
        page=value.page,
        page_size=value.page_size,
        total=value.total,
        pages=value.pages,
    )


def _position(value: PaperPositionDetail) -> PaperPositionResponse:
    return PaperPositionResponse(**asdict(value))


def _position_page(
    value: PaperPage[PaperPositionDetail],
) -> PaperPositionPageResponse:
    return PaperPositionPageResponse(
        items=[_position(item) for item in value.items],
        page=value.page,
        page_size=value.page_size,
        total=value.total,
        pages=value.pages,
    )


def _settlement(value: PaperSettlementDetail) -> PaperSettlementResponse:
    return PaperSettlementResponse(**asdict(value))


def _settlement_page(
    value: PaperPage[PaperSettlementDetail],
) -> PaperSettlementPageResponse:
    return PaperSettlementPageResponse(
        items=[_settlement(item) for item in value.items],
        page=value.page,
        page_size=value.page_size,
        total=value.total,
        pages=value.pages,
    )


def _equity_point(value: EquityCurvePoint) -> EquityCurvePointResponse:
    return EquityCurvePointResponse(**asdict(value))


def _performance(value: PaperPerformanceReport) -> PaperPerformanceResponse:
    metrics = value.metrics
    return PaperPerformanceResponse(
        portfolio=_portfolio(value.portfolio),
        metrics=PaperMetricsResponse(
            initial_capital=metrics.initial_capital,
            final_capital=metrics.final_capital,
            net_profit=metrics.net_profit,
            simulated_roi=metrics.simulated_roi,
            realized_pnl=metrics.realized_pnl,
            unrealized_pnl=metrics.unrealized_pnl,
            total_costs=metrics.total_costs,
            decision_count=metrics.decision_count,
            open_trade_count=metrics.open_trade_count,
            closed_trade_count=metrics.closed_trade_count,
            abstention_count=metrics.abstention_count,
            rejection_count=metrics.rejection_count,
            win_rate=metrics.win_rate,
            average_profit=metrics.average_profit,
            average_loss=metrics.average_loss,
            profit_factor=metrics.profit_factor,
            maximum_drawdown=metrics.maximum_drawdown,
            maximum_exposure=metrics.maximum_exposure,
            coverage=metrics.coverage,
            independent_resolved_markets=metrics.independent_resolved_markets,
            largest_trade_profit_share=metrics.largest_trade_profit_share,
            evidence_state=metrics.evidence_state,
            by_category=[StrategyBreakdownResponse(**asdict(item)) for item in metrics.by_category],
            by_opportunity_level=[
                StrategyBreakdownResponse(**asdict(item)) for item in metrics.by_opportunity_level
            ],
            by_edge_range=[
                StrategyBreakdownResponse(**asdict(item)) for item in metrics.by_edge_range
            ],
            by_confidence_range=[
                StrategyBreakdownResponse(**asdict(item)) for item in metrics.by_confidence_range
            ],
        ),
        baselines=[BaselinePerformanceResponse(**asdict(item)) for item in value.baselines],
        alerts=[SimulationAlertResponse(**asdict(item)) for item in value.alerts],
        strategy_configuration_hash=value.strategy_configuration_hash,
        simulation_only=value.simulation_only,
    )
