from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from predictionlab.application.sources import (
    SourceHealthItem,
    SourceHealthQueryService,
)

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceHealthResponse(BaseModel):
    code: str
    name: str
    status: str
    checked_at: datetime
    latency_ms: float = Field(ge=0)
    safe_error_type: str | None


def get_source_health_service(request: Request) -> SourceHealthQueryService:
    return cast(
        SourceHealthQueryService,
        request.app.state.source_health_service,
    )


@router.get(
    "",
    response_model=list[SourceHealthResponse],
    summary="List configured source health",
    operation_id="list_source_health",
)
async def list_source_health(
    service: Annotated[
        SourceHealthQueryService,
        Depends(get_source_health_service),
    ],
) -> list[SourceHealthResponse]:
    return [_response(item) for item in await service.list()]


def _response(item: SourceHealthItem) -> SourceHealthResponse:
    return SourceHealthResponse(
        code=item.code,
        name=item.name,
        status=item.status,
        checked_at=item.checked_at,
        latency_ms=item.latency_ms,
        safe_error_type=item.safe_error_type,
    )
