from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field

from predictionlab.application.health import ReadinessChecker

router = APIRouter(tags=["system"])


class LivenessResponse(BaseModel):
    status: str


class ComponentHealthResponse(BaseModel):
    name: str
    status: str
    latency_ms: float = Field(ge=0.0)


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ComponentHealthResponse]


def get_readiness_checker(request: Request) -> ReadinessChecker:
    return cast(ReadinessChecker, request.app.state.readiness_checker)


@router.get(
    "/health/live",
    summary="Process liveness",
    response_model=LivenessResponse,
)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/health/ready",
    summary="Dependency readiness",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "One or more required dependencies are unavailable."
        }
    },
)
async def readiness(
    response: Response,
    checker: Annotated[ReadinessChecker, Depends(get_readiness_checker)],
) -> ReadinessResponse:
    report = await checker.check()
    readiness_status = "ready" if report.ready else "not_ready"
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=readiness_status,
        checks=[
            ComponentHealthResponse(
                name=check.name,
                status=check.status.value,
                latency_ms=check.latency_ms,
            )
            for check in report.checks
        ],
    )
