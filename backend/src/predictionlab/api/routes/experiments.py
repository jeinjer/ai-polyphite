from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from predictionlab.application.experiments import (
    ExperimentRunDetail,
    ExperimentRunNotFoundError,
    ExperimentRunPage,
    ExperimentRunQueryService,
    ListExperimentRuns,
    ReplayDatasetQueryService,
    ReplayDatasetSummary,
)
from predictionlab.domain.experiments import ExperimentRunStatus

router = APIRouter(tags=["experiments"])


class ExperimentRunResponse(BaseModel):
    experiment_run_id: UUID
    dataset_id: str
    dataset_version: str
    started_at: datetime
    finished_at: datetime | None
    status: ExperimentRunStatus
    replay_start: datetime
    replay_end: datetime
    random_seed: int = Field(ge=0)
    configuration_hash: str
    code_version: str | None
    result_hash: str | None
    correlation_id: str
    safe_error_type: str | None
    reproducible: bool


class ExperimentRunPageResponse(BaseModel):
    items: list[ExperimentRunResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class ReplayDatasetResponse(BaseModel):
    dataset_id: str
    version: str
    schema_version: str
    created_at: datetime
    description: str
    content_sha256: str
    replay_start: datetime
    replay_end: datetime
    market_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)


def get_experiment_query_service(request: Request) -> ExperimentRunQueryService:
    return cast(
        ExperimentRunQueryService,
        request.app.state.experiment_run_query_service,
    )


def get_dataset_query_service(request: Request) -> ReplayDatasetQueryService:
    return cast(
        ReplayDatasetQueryService,
        request.app.state.replay_dataset_query_service,
    )


@router.get(
    "/experiment-runs",
    response_model=ExperimentRunPageResponse,
    summary="List reproducible experiment runs",
    operation_id="list_experiment_runs",
)
async def list_experiment_runs(
    service: Annotated[
        ExperimentRunQueryService,
        Depends(get_experiment_query_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    run_status: Annotated[
        ExperimentRunStatus | None,
        Query(alias="status"),
    ] = None,
) -> ExperimentRunPageResponse:
    result = await service.list(
        ListExperimentRuns(
            page=page,
            page_size=page_size,
            dataset_id=dataset,
            status=run_status,
        )
    )
    return _page_response(result)


@router.get(
    "/experiment-runs/{run_id}",
    response_model=ExperimentRunResponse,
    summary="Get a reproducible experiment run",
    operation_id="get_experiment_run",
)
async def get_experiment_run(
    run_id: UUID,
    service: Annotated[
        ExperimentRunQueryService,
        Depends(get_experiment_query_service),
    ],
) -> ExperimentRunResponse:
    try:
        result = await service.get(run_id)
    except ExperimentRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment run not found.",
        ) from exc
    return _response(result)


@router.get(
    "/replay-datasets",
    response_model=list[ReplayDatasetResponse],
    summary="List validated local replay datasets",
    operation_id="list_replay_datasets",
)
async def list_replay_datasets(
    service: Annotated[
        ReplayDatasetQueryService,
        Depends(get_dataset_query_service),
    ],
) -> list[ReplayDatasetResponse]:
    return [_dataset_response(item) for item in service.list()]


def _response(run: ExperimentRunDetail) -> ExperimentRunResponse:
    return ExperimentRunResponse(**asdict(run))


def _page_response(page: ExperimentRunPage) -> ExperimentRunPageResponse:
    return ExperimentRunPageResponse(
        items=[_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )


def _dataset_response(dataset: ReplayDatasetSummary) -> ReplayDatasetResponse:
    return ReplayDatasetResponse(**asdict(dataset))
