"""Minimal operator controls for autonomous paper operation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from predictionlab.application.automation import AutomationControlService, AutomationState

router = APIRouter(prefix="/automation", tags=["automation"])


class AutomationStateResponse(BaseModel):
    paused: bool
    updated_at: datetime | None
    reason: str | None
    simulation_only: bool = True


class PauseAutomationRequest(BaseModel):
    reason: str = Field(
        default="Pausa solicitada desde el dashboard.",
        min_length=1,
        max_length=500,
    )


def get_automation_service(request: Request) -> AutomationControlService:
    return cast(
        AutomationControlService,
        request.app.state.automation_control_service,
    )


@router.get(
    "",
    response_model=AutomationStateResponse,
    summary="Read autonomous paper-operation status",
)
async def get_automation_state(
    service: Annotated[AutomationControlService, Depends(get_automation_service)],
) -> AutomationStateResponse:
    return _response(await service.status())


@router.post(
    "/pause",
    response_model=AutomationStateResponse,
    summary="Pause future automatic predictions and paper operations",
)
async def pause_automation(
    payload: PauseAutomationRequest,
    service: Annotated[AutomationControlService, Depends(get_automation_service)],
) -> AutomationStateResponse:
    return _response(await service.pause(reason=payload.reason))


@router.post(
    "/resume",
    response_model=AutomationStateResponse,
    summary="Resume automatic predictions and paper operations",
)
async def resume_automation(
    service: Annotated[AutomationControlService, Depends(get_automation_service)],
) -> AutomationStateResponse:
    return _response(await service.resume())


def _response(state: AutomationState) -> AutomationStateResponse:
    return AutomationStateResponse(
        paused=state.paused,
        updated_at=state.updated_at,
        reason=state.reason,
    )
