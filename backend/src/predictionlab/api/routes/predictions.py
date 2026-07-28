"""Read API and development-only manual trigger for predictions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from predictionlab.application.predictions import (
    AgentPredictionDetail,
    CalibrationBucket,
    ListPredictions,
    MetricSummary,
    PredictionEvaluationReport,
    PredictionEvaluationService,
    PredictionIdempotencyConflictError,
    PredictionMarketNotFoundError,
    PredictionNotFoundError,
    PredictionOrchestrator,
    PredictionQueryService,
    PredictionRunDetail,
    PredictionRunPage,
    RunPrediction,
)
from predictionlab.core.context import get_correlation_id
from predictionlab.core.settings import AppEnvironment
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    JsonScalar,
    Recommendation,
)
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus

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
    response_model=PredictionRunPageResponse,
    summary="List reproducible prediction runs",
    operation_id="list_predictions",
)
async def list_predictions(
    service: Annotated[PredictionQueryService, Depends(get_prediction_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    predicted_from: Annotated[datetime | None, Query(alias="from")] = None,
    predicted_to: Annotated[datetime | None, Query(alias="to")] = None,
    market_id: UUID | None = None,
    category: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    recommendation: Recommendation | None = None,
    run_status: Annotated[
        PredictionRunStatus | None,
        Query(alias="status"),
    ] = None,
    opportunity_level: OpportunityLevel | None = None,
    experiment_run_id: UUID | None = None,
) -> PredictionRunPageResponse:
    result = await service.list(
        ListPredictions(
            page=page,
            page_size=page_size,
            predicted_from=predicted_from,
            predicted_to=predicted_to,
            market_id=market_id,
            category=category,
            recommendation=recommendation,
            status=run_status,
            opportunity_level=opportunity_level,
            experiment_run_id=experiment_run_id,
        )
    )
    return _page_response(result)


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
    return _evaluation_response(
        await service.evaluate(experiment_run_id=experiment_id)
    )


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
    if (
        settings.app_env is AppEnvironment.PRODUCTION
        or not settings.enable_manual_prediction_runs
    ):
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
            detail=(
                "A prediction with the same idempotency scope contains "
                "different input data."
            ),
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
