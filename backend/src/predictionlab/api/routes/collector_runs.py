from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)
from predictionlab.application.collectors.service import (
    CollectorRunNotFoundError,
    CollectorRunQueryService,
)
from predictionlab.collectors.models import CollectorRunStatus

router = APIRouter(prefix="/collector-runs", tags=["collector-runs"])


class CollectorRunResponse(BaseModel):
    run_id: UUID
    provider_code: str
    started_at: datetime
    finished_at: datetime | None
    status: CollectorRunStatus
    markets_fetched: int = Field(ge=0)
    markets_created: int = Field(ge=0)
    markets_updated: int = Field(ge=0)
    markets_unchanged: int = Field(ge=0)
    observations_fetched: int = Field(ge=0)
    observations_created: int = Field(ge=0)
    observations_duplicated: int = Field(ge=0)
    observations_skipped: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    duration_ms: float | None = Field(default=None, ge=0)
    safe_error_type: str | None
    correlation_id: str


class CollectorRunPageResponse(BaseModel):
    items: list[CollectorRunResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


def get_collector_run_query_service(
    request: Request,
) -> CollectorRunQueryService:
    return cast(
        CollectorRunQueryService,
        request.app.state.collector_run_query_service,
    )


@router.get(
    "",
    response_model=CollectorRunPageResponse,
    summary="List collector runs",
    operation_id="list_collector_runs",
)
async def list_collector_runs(
    service: Annotated[
        CollectorRunQueryService,
        Depends(get_collector_run_query_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    provider: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    run_status: Annotated[
        CollectorRunStatus | None,
        Query(alias="status"),
    ] = None,
    started_from: Annotated[
        datetime | None,
        Query(alias="from"),
    ] = None,
    started_to: Annotated[
        datetime | None,
        Query(alias="to"),
    ] = None,
) -> CollectorRunPageResponse:
    result = await service.list(
        ListCollectorRuns(
            page=page,
            page_size=page_size,
            provider_code=provider,
            status=run_status,
            started_from=started_from,
            started_to=started_to,
        )
    )
    return _page_response(result)


@router.get(
    "/{run_id}",
    response_model=CollectorRunResponse,
    summary="Get collector run",
    operation_id="get_collector_run",
)
async def get_collector_run(
    run_id: UUID,
    service: Annotated[
        CollectorRunQueryService,
        Depends(get_collector_run_query_service),
    ],
) -> CollectorRunResponse:
    try:
        result = await service.get(run_id)
    except CollectorRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector run not found.",
        ) from exc
    return _response(result)


def _response(run: CollectorRunDetail) -> CollectorRunResponse:
    return CollectorRunResponse(**asdict(run))


def _page_response(page: CollectorRunPage) -> CollectorRunPageResponse:
    return CollectorRunPageResponse(
        items=[_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )
