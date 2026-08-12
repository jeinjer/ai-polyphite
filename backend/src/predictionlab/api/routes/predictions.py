"""Read API and development-only manual trigger for predictions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from predictionlab.application.predictions import (
    AgentPredictionDetail,
    CalibrationBucket,
    EstimatedOutcomeFilter,
    ListPredictions,
    MetricSummary,
    PredictionEvaluationReport,
    PredictionEvaluationService,
    PredictionIdempotencyConflictError,
    PredictionListItem,
    PredictionListPage,
    PredictionMarketNotFoundError,
    PredictionNotFoundError,
    PredictionOrchestrator,
    PredictionQueryService,
    PredictionRunDetail,
    PredictionRunPage,
    PredictionSort,
    RunPrediction,
    SortDirection,
)
from predictionlab.core.context import get_correlation_id
from predictionlab.core.settings import AppEnvironment
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    JsonScalar,
    Recommendation,
)
from predictionlab.domain.commercial_evaluations import (
    CommercialEvaluation,
    CommercialLabel,
    DataFreshnessStatus,
    PotentialSide,
)
from predictionlab.domain.paper_trading import (
    PositionSide,
    TradeDecisionSource,
    TradeDecisionType,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    OpportunityLevel,
    PredictionRunStatus,
)

router = APIRouter(tags=["predictions"])


class AgentEvidenceResponse(BaseModel):
    code: str
    summary: str
    direction: EvidenceDirection
    strength: Decimal = Field(ge=0, le=1)


class AgentPredictionResponse(BaseModel):
    agent_prediction_id: UUID
    agent_name: str
    agent_version: str
    predicted_probability: Decimal | None = Field(default=None, ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    recommendation: Recommendation
    rationale_summary: str
    evidence: list[AgentEvidenceResponse]
    warnings: list[str]
    input_hash: str
    output_hash: str
    duration_ms: Decimal = Field(ge=0)
    disagreement_score: Decimal | None = Field(default=None, ge=0, le=1)
    agent_weights: dict[str, Decimal]


class PredictionRunResponse(BaseModel):
    prediction_run_id: UUID
    experiment_run_id: UUID | None
    market_id: UUID
    market_title: str
    category: str | None
    predicted_at: datetime
    market_probability: Decimal | None = Field(default=None, ge=0, le=1)
    consensus_probability: Decimal | None = Field(default=None, ge=0, le=1)
    consensus_confidence: Decimal = Field(ge=0, le=1)
    recommendation: Recommendation
    edge: Decimal | None = Field(default=None, ge=-1, le=1)
    no_edge: Decimal | None = Field(default=None, ge=-1, le=1)
    opportunity_level: OpportunityLevel
    disagreement_score: Decimal = Field(ge=0, le=1)
    status: PredictionRunStatus
    agent_configuration_hash: str
    input_hash: str
    result_hash: str
    duration_ms: Decimal = Field(ge=0)
    safe_error_type: str | None
    abstention_reason: str | None
    correlation_id: str
    causation_id: str | None
    created_at: datetime
    agent_weights: dict[str, Decimal]
    agent_predictions: list[AgentPredictionResponse]
    estimated_outcome: EstimatedOutcome | None = None
    market_status: str | None = None
    provider_code: str | None = None
    commercial_evaluation: CommercialEvaluationResponse | None = None
    related_executions: list[RelatedPaperExecutionResponse] = Field(default_factory=list)


class CommercialEvaluationResponse(BaseModel):
    evaluation_id: UUID
    portfolio_id: UUID | None
    campaign_id: str
    evaluated_at: datetime
    estimated_outcome: EstimatedOutcome | None
    potential_side: PotentialSide
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    gross_edge: Decimal | None
    estimated_fees: Decimal
    estimated_slippage: Decimal
    estimated_other_costs: Decimal
    net_edge: Decimal | None
    confidence: Decimal
    commercial_label: CommercialLabel
    is_actionable: bool
    reasons: list[str]
    warnings: list[str]
    data_freshness_status: DataFreshnessStatus
    portfolio_has_open_position: bool


class PredictionListItemResponse(BaseModel):
    prediction_run_id: UUID
    market_id: UUID
    market_title: str
    provider_code: str
    category: str | None
    predicted_at: datetime
    market_probability: Decimal | None
    consensus_probability: Decimal | None
    consensus_confidence: Decimal
    estimated_outcome: EstimatedOutcome | None
    commercial_label: CommercialLabel
    potential_side: PotentialSide
    gross_edge: Decimal | None
    net_edge: Decimal | None
    is_actionable: bool
    primary_reason: str
    portfolio_has_open_position: bool
    data_freshness_status: DataFreshnessStatus
    campaign_id: str | None
    portfolio_id: UUID | None


class PredictionListPageResponse(BaseModel):
    items: list[PredictionListItemResponse]
    page: int
    page_size: Literal[25, 50]
    total_items: int
    total_pages: int
    applied_filters: dict[str, str]


class RelatedPaperExecutionResponse(BaseModel):
    decision_id: UUID
    portfolio_id: UUID
    portfolio_name: str
    decision: TradeDecisionType
    decision_source: TradeDecisionSource
    override_reason: str | None
    side: PositionSide | None
    decided_at: datetime
    order_id: UUID | None
    trade_id: UUID | None
    position_id: UUID | None


class PredictionRunPageResponse(BaseModel):
    items: list[PredictionRunResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class ManualPredictionRequest(BaseModel):
    market_id: UUID
    predicted_at: datetime | None = None
    experiment_run_id: UUID | None = None
    random_seed: int = Field(default=0, ge=0)
    context: dict[str, JsonScalar] = Field(default_factory=dict)
    model_configuration: dict[str, JsonScalar] = Field(default_factory=dict)
    causation_id: str | None = Field(default=None, min_length=1, max_length=200)


class MetricSummaryResponse(BaseModel):
    brier_score: Decimal = Field(ge=0)
    log_loss: Decimal = Field(ge=0)
    absolute_error: Decimal = Field(ge=0)
    directional_accuracy: Decimal = Field(ge=0, le=1)


class CalibrationBucketResponse(BaseModel):
    lower_bound: Decimal = Field(ge=0, le=1)
    upper_bound: Decimal = Field(ge=0, le=1)
    prediction_count: int = Field(ge=1)
    mean_probability: Decimal = Field(ge=0, le=1)
    observed_frequency: Decimal = Field(ge=0, le=1)


class PredictionEvaluationResponse(BaseModel):
    experiment_run_id: UUID | None
    resolved_count: int = Field(ge=0)
    emitted_count: int = Field(ge=0)
    abstained_count: int = Field(ge=0)
    coverage: Decimal = Field(ge=0, le=1)
    system: MetricSummaryResponse | None
    market_baseline: MetricSummaryResponse | None
    constant_baseline: MetricSummaryResponse | None
    calibration: list[CalibrationBucketResponse]


def get_prediction_query_service(request: Request) -> PredictionQueryService:
    return cast(PredictionQueryService, request.app.state.prediction_query_service)


def get_prediction_orchestrator(request: Request) -> PredictionOrchestrator:
    return cast(PredictionOrchestrator, request.app.state.prediction_orchestrator)


def get_prediction_evaluation_service(
    request: Request,
) -> PredictionEvaluationService:
    return cast(
        PredictionEvaluationService,
        request.app.state.prediction_evaluation_service,
    )


@router.get(
    "/predictions",
    response_model=PredictionListPageResponse,
    summary="List lightweight prediction and commercial summaries",
    operation_id="list_predictions",
)
async def list_predictions(
    service: Annotated[PredictionQueryService, Depends(get_prediction_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=25, le=50)] = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    market_id: UUID | None = None,
    category: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    provider: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    commercial_label: Annotated[
        Literal["all", "actionable", "not_actionable", "not_evaluable"],
        Query(),
    ] = "all",
    estimated_outcome: EstimatedOutcomeFilter | None = None,
    portfolio_id: UUID | None = None,
    campaign_id: Annotated[
        str | None,
        Query(min_length=1, max_length=160),
    ] = None,
    sort: PredictionSort = PredictionSort.PREDICTED_AT,
    direction: SortDirection = SortDirection.DESC,
    recommendation: Recommendation | None = None,
    run_status: Annotated[
        PredictionRunStatus | None,
        Query(alias="status"),
    ] = None,
    opportunity_level: OpportunityLevel | None = None,
    experiment_run_id: UUID | None = None,
) -> PredictionListPageResponse:
    if page_size not in {25, 50}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="page_size must be 25 or 50.",
        )
    result = await service.list_summary(
        ListPredictions(
            page=page,
            page_size=page_size,
            predicted_from=date_from,
            predicted_to=date_to,
            market_id=market_id,
            category=category,
            recommendation=recommendation,
            status=run_status,
            opportunity_level=opportunity_level,
            experiment_run_id=experiment_run_id,
            provider=provider,
            commercial_label=(
                None if commercial_label == "all" else CommercialLabel(commercial_label)
            ),
            estimated_outcome_filter=estimated_outcome,
            portfolio_id=portfolio_id,
            campaign_id=campaign_id,
            sort=sort,
            direction=direction,
        )
    )
    return _list_page_response(result)


@router.get(
    "/predictions/{prediction_id}",
    response_model=PredictionRunResponse,
    summary="Get a fully traceable prediction",
    operation_id="get_prediction",
)
async def get_prediction(
    prediction_id: UUID,
    service: Annotated[PredictionQueryService, Depends(get_prediction_query_service)],
) -> PredictionRunResponse:
    try:
        return _response(await service.get(prediction_id))
    except PredictionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found.",
        ) from exc


@router.get(
    "/agent-predictions",
    response_model=PredictionRunPageResponse,
    summary="List recent full agent outputs for the engineering view",
    operation_id="list_agent_predictions",
)
async def list_agent_predictions(
    service: Annotated[
        PredictionQueryService,
        Depends(get_prediction_query_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PredictionRunPageResponse:
    return _page_response(await service.list(ListPredictions(page=page, page_size=page_size)))


@router.get(
    "/markets/{market_id}/predictions",
    response_model=PredictionRunPageResponse,
    summary="List prediction history for a market",
    operation_id="list_market_predictions",
)
async def list_market_predictions(
    market_id: UUID,
    service: Annotated[PredictionQueryService, Depends(get_prediction_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PredictionRunPageResponse:
    return _page_response(
        await service.list(
            ListPredictions(
                market_id=market_id,
                page=page,
                page_size=page_size,
            )
        )
    )


@router.get(
    "/experiment-runs/{experiment_id}/predictions",
    response_model=PredictionRunPageResponse,
    summary="List predictions produced by an experiment",
    operation_id="list_experiment_predictions",
)
async def list_experiment_predictions(
    experiment_id: UUID,
    service: Annotated[PredictionQueryService, Depends(get_prediction_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PredictionRunPageResponse:
    return _page_response(
        await service.list(
            ListPredictions(
                experiment_run_id=experiment_id,
                page=page,
                page_size=page_size,
            )
        )
    )


@router.get(
    "/prediction-evaluation",
    response_model=PredictionEvaluationResponse,
    summary="Evaluate the latest live prediction per resolved market",
    operation_id="evaluate_live_predictions",
)
async def evaluate_live_predictions(
    service: Annotated[
        PredictionEvaluationService,
        Depends(get_prediction_evaluation_service),
    ],
) -> PredictionEvaluationResponse:
    return _evaluation_response(await service.evaluate(experiment_run_id=None))


@router.get(
    "/experiment-runs/{experiment_id}/prediction-evaluation",
    response_model=PredictionEvaluationResponse,
    summary="Evaluate predictions after binary market resolution",
    operation_id="evaluate_experiment_predictions",
)
async def evaluate_experiment_predictions(
    experiment_id: UUID,
    service: Annotated[
        PredictionEvaluationService,
        Depends(get_prediction_evaluation_service),
    ],
) -> PredictionEvaluationResponse:
    return _evaluation_response(await service.evaluate(experiment_run_id=experiment_id))


@router.post(
    "/predictions/run",
    response_model=PredictionRunResponse,
    summary="Run one prediction in a development environment",
    operation_id="run_prediction_manually",
)
async def run_prediction_manually(
    payload: ManualPredictionRequest,
    request: Request,
    orchestrator: Annotated[
        PredictionOrchestrator,
        Depends(get_prediction_orchestrator),
    ],
    query_service: Annotated[
        PredictionQueryService,
        Depends(get_prediction_query_service),
    ],
) -> PredictionRunResponse:
    settings = request.app.state.settings
    if settings.app_env is AppEnvironment.PRODUCTION or not settings.enable_manual_prediction_runs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual prediction runs are disabled.",
        )
    try:
        run = await orchestrator.run(
            RunPrediction(
                market_id=payload.market_id,
                predicted_at=payload.predicted_at or orchestrator.now(),
                experiment_run_id=payload.experiment_run_id,
                random_seed=payload.random_seed,
                context=payload.context,
                model_configuration=payload.model_configuration,
                correlation_id=get_correlation_id(),
                causation_id=payload.causation_id,
            )
        )
    except PredictionMarketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found at the requested timestamp.",
        ) from exc
    except PredictionIdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("A prediction with the same idempotency scope contains different input data."),
        ) from exc
    return _response(await query_service.get(run.prediction_run_id))


def _page_response(page: PredictionRunPage) -> PredictionRunPageResponse:
    return PredictionRunPageResponse(
        items=[_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )


def _list_page_response(
    page: PredictionListPage,
) -> PredictionListPageResponse:
    return PredictionListPageResponse(
        items=[_list_item_response(item) for item in page.items],
        page=page.page,
        page_size=cast(Literal[25, 50], page.page_size),
        total_items=page.total_items,
        total_pages=page.total_pages,
        applied_filters=page.applied_filters,
    )


def _list_item_response(
    item: PredictionListItem,
) -> PredictionListItemResponse:
    return PredictionListItemResponse(
        prediction_run_id=item.prediction_run_id,
        market_id=item.market_id,
        market_title=item.market_title,
        provider_code=item.provider_code,
        category=item.category,
        predicted_at=item.predicted_at,
        market_probability=item.market_probability,
        consensus_probability=item.consensus_probability,
        consensus_confidence=item.consensus_confidence,
        estimated_outcome=item.estimated_outcome,
        commercial_label=item.commercial_label,
        potential_side=item.potential_side,
        gross_edge=item.gross_edge,
        net_edge=item.net_edge,
        is_actionable=item.is_actionable,
        primary_reason=item.primary_reason,
        portfolio_has_open_position=(item.portfolio_has_open_position),
        data_freshness_status=item.data_freshness_status,
        campaign_id=item.campaign_id,
        portfolio_id=item.portfolio_id,
    )


def _response(run: PredictionRunDetail) -> PredictionRunResponse:
    return PredictionRunResponse(
        prediction_run_id=run.prediction_run_id,
        experiment_run_id=run.experiment_run_id,
        market_id=run.market_id,
        market_title=run.market_title,
        category=run.category,
        predicted_at=run.predicted_at,
        market_probability=run.market_probability,
        consensus_probability=run.consensus_probability,
        consensus_confidence=run.consensus_confidence,
        recommendation=run.recommendation,
        edge=run.edge,
        no_edge=run.no_edge,
        opportunity_level=run.opportunity_level,
        disagreement_score=run.disagreement_score,
        status=run.status,
        agent_configuration_hash=run.agent_configuration_hash,
        input_hash=run.input_hash,
        result_hash=run.result_hash,
        duration_ms=run.duration_ms,
        safe_error_type=run.safe_error_type,
        abstention_reason=run.abstention_reason,
        correlation_id=run.correlation_id,
        causation_id=run.causation_id,
        created_at=run.created_at,
        agent_weights=run.agent_weights,
        agent_predictions=[_agent_response(item) for item in run.agent_predictions],
        estimated_outcome=run.estimated_outcome,
        market_status=(run.market_status.value if run.market_status is not None else None),
        provider_code=run.provider_code,
        commercial_evaluation=(
            _commercial_response(run.commercial_evaluation)
            if run.commercial_evaluation is not None
            else None
        ),
        related_executions=[
            RelatedPaperExecutionResponse(
                decision_id=item.decision_id,
                portfolio_id=item.portfolio_id,
                portfolio_name=item.portfolio_name,
                decision=item.decision,
                decision_source=item.decision_source,
                override_reason=item.override_reason,
                side=item.side,
                decided_at=item.decided_at,
                order_id=item.order_id,
                trade_id=item.trade_id,
                position_id=item.position_id,
            )
            for item in run.related_executions
        ],
    )


def _commercial_response(
    evaluation: CommercialEvaluation,
) -> CommercialEvaluationResponse:
    return CommercialEvaluationResponse(
        evaluation_id=evaluation.evaluation_id,
        portfolio_id=evaluation.portfolio_id,
        campaign_id=evaluation.campaign_id,
        evaluated_at=evaluation.evaluated_at,
        estimated_outcome=evaluation.estimated_outcome,
        potential_side=evaluation.potential_side,
        market_probability=evaluation.market_probability,
        consensus_probability=evaluation.consensus_probability,
        gross_edge=evaluation.gross_edge,
        estimated_fees=evaluation.estimated_fees,
        estimated_slippage=evaluation.estimated_slippage,
        estimated_other_costs=evaluation.estimated_other_costs,
        net_edge=evaluation.net_edge,
        confidence=evaluation.confidence,
        commercial_label=evaluation.commercial_label,
        is_actionable=evaluation.is_actionable,
        reasons=list(evaluation.reasons),
        warnings=list(evaluation.warnings),
        data_freshness_status=evaluation.data_freshness_status,
        portfolio_has_open_position=(evaluation.portfolio_has_open_position),
    )


def _agent_response(item: AgentPredictionDetail) -> AgentPredictionResponse:
    return AgentPredictionResponse(
        agent_prediction_id=item.agent_prediction_id,
        agent_name=item.agent_name,
        agent_version=item.agent_version,
        predicted_probability=item.predicted_probability,
        confidence=item.confidence,
        recommendation=item.recommendation,
        rationale_summary=item.rationale_summary,
        evidence=[_evidence_response(value) for value in item.evidence],
        warnings=list(item.warnings),
        input_hash=item.input_hash,
        output_hash=item.output_hash,
        duration_ms=item.duration_ms,
        disagreement_score=item.disagreement_score,
        agent_weights=item.agent_weights,
    )


def _evidence_response(item: AgentEvidence) -> AgentEvidenceResponse:
    return AgentEvidenceResponse(
        code=item.code,
        summary=item.summary,
        direction=item.direction,
        strength=item.strength,
    )


def _evaluation_response(
    report: PredictionEvaluationReport,
) -> PredictionEvaluationResponse:
    return PredictionEvaluationResponse(
        experiment_run_id=report.experiment_run_id,
        resolved_count=report.resolved_count,
        emitted_count=report.emitted_count,
        abstained_count=report.abstained_count,
        coverage=report.coverage,
        system=_metric_response(report.system),
        market_baseline=_metric_response(report.market_baseline),
        constant_baseline=_metric_response(report.constant_baseline),
        calibration=[_calibration_response(item) for item in report.calibration],
    )


def _metric_response(item: MetricSummary | None) -> MetricSummaryResponse | None:
    return (
        MetricSummaryResponse(
            brier_score=item.brier_score,
            log_loss=item.log_loss,
            absolute_error=item.absolute_error,
            directional_accuracy=item.directional_accuracy,
        )
        if item is not None
        else None
    )


def _calibration_response(item: CalibrationBucket) -> CalibrationBucketResponse:
    return CalibrationBucketResponse(
        lower_bound=item.lower_bound,
        upper_bound=item.upper_bound,
        prediction_count=item.prediction_count,
        mean_probability=item.mean_probability,
        observed_frequency=item.observed_frequency,
    )
