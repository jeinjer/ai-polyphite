"""Normalized provider health-check result."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from predictionlab.core.clock import SystemClock
from predictionlab.providers.base.models import ProviderDto, _as_utc


class ProviderHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ProviderHealth(ProviderDto):
    provider_code: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$",
        ),
    ]
    status: ProviderHealthStatus
    checked_at: datetime = Field(default_factory=SystemClock().now)
    latency_ms: float = Field(ge=0)
    error_type: Annotated[str, StringConstraints(min_length=1, max_length=200)] | None = None

    _normalize_checked_at = field_validator("checked_at", mode="after")(_as_utc)
