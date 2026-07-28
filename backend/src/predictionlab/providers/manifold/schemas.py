"""Validation models for the subset of the public Manifold API we consume."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ManifoldMarketPayload(BaseModel):
    """Tolerant input schema: known fields are strict, API additions are ignored."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    market_id: Annotated[str, StringConstraints(min_length=1, max_length=512)] = Field(alias="id")
    question: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    outcome_type: Annotated[str, StringConstraints(min_length=1)] = Field(alias="outcomeType")
    created_time: int = Field(alias="createdTime", ge=0)
    close_time: int | None = Field(default=None, alias="closeTime", ge=0)
    last_updated_time: int | None = Field(
        default=None,
        alias="lastUpdatedTime",
        ge=0,
    )
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    total_liquidity: Decimal | None = Field(
        default=None,
        alias="totalLiquidity",
        ge=0,
    )
    is_resolved: bool = Field(default=False, alias="isResolved")
    resolution: str | None = None
    resolution_time: int | None = Field(
        default=None,
        alias="resolutionTime",
        ge=0,
    )
    text_description: Annotated[str, StringConstraints(max_length=20_000)] | None = Field(
        default=None, alias="textDescription"
    )
    group_slugs: tuple[str, ...] = Field(default=(), alias="groupSlugs")
