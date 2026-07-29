"""Normalized external DTOs returned by market-data providers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

ExternalMarketId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=512),
]
ExternalCursor = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
]


class ProviderDto(BaseModel):
    """Strict, immutable base for values crossing the provider boundary."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class ProviderMarketStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ProviderResolutionOutcome(StrEnum):
    UNRESOLVED = "unresolved"
    YES = "yes"
    NO = "no"
    CANCELLED = "cancelled"
    OTHER = "other"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must include timezone information")
    return value.astimezone(UTC)


class ProviderMarket(ProviderDto):
    """Provider-neutral representation of one external market."""

    provider_market_id: ExternalMarketId
    title: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    description: Annotated[str, StringConstraints(max_length=20_000)] | None = None
    category: Annotated[str, StringConstraints(max_length=200)] | None = None
    status: ProviderMarketStatus
    resolution_at: datetime | None = None
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None
    resolution_outcome: ProviderResolutionOutcome = ProviderResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: (
        Annotated[
            str,
            StringConstraints(max_length=200),
        ]
        | None
    ) = None

    _normalize_datetimes = field_validator(
        "resolution_at",
        "source_created_at",
        "source_updated_at",
        "resolved_at",
        mode="after",
    )(_as_utc)


class ProviderMarketSnapshot(ProviderDto):
    """Provider-neutral observation of market prices and liquidity."""

    provider_market_id: ExternalMarketId
    observed_at: datetime
    yes_price: Decimal | None = Field(default=None, ge=0, le=1)
    no_price: Decimal | None = Field(default=None, ge=0, le=1)
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    spread: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    liquidity: Decimal | None = Field(default=None, ge=0)

    _normalize_observed_at = field_validator("observed_at", mode="after")(_as_utc)


class ProviderMarketObservation(ProviderDto):
    """Non-executable observation of public market activity."""

    provider_market_id: ExternalMarketId
    observed_at: datetime
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    liquidity: Decimal | None = Field(default=None, ge=0)
    source_updated_at: datetime | None = None
    raw_payload_hash: (
        Annotated[
            str,
            StringConstraints(pattern=r"^[0-9a-f]{64}$"),
        ]
        | None
    ) = None

    _normalize_datetimes = field_validator(
        "observed_at",
        "source_updated_at",
        mode="after",
    )(_as_utc)

    @model_validator(mode="after")
    def require_value(self) -> ProviderMarketObservation:
        if all(value is None for value in (self.probability, self.volume, self.liquidity)):
            raise ValueError("observation must contain probability, volume or liquidity")
        return self


class FetchMarketsRequest(ProviderDto):
    """Provider catalog query using opaque cursor pagination."""

    cursor: ExternalCursor | None = None
    limit: int = Field(default=100, ge=1, le=1_000)
    updated_after: datetime | None = None
    statuses: frozenset[ProviderMarketStatus] = frozenset()

    _normalize_updated_after = field_validator("updated_after", mode="after")(_as_utc)


class MarketBatch(ProviderDto):
    markets: tuple[ProviderMarket, ...]
    next_cursor: ExternalCursor | None = None


class FetchSnapshotsRequest(ProviderDto):
    """Historical snapshot query for one external market."""

    provider_market_id: ExternalMarketId
    cursor: ExternalCursor | None = None
    limit: int = Field(default=100, ge=1, le=500)
    observed_after: datetime | None = None

    _normalize_observed_after = field_validator("observed_after", mode="after")(_as_utc)


class SnapshotBatch(ProviderDto):
    snapshots: tuple[ProviderMarketSnapshot, ...]
    next_cursor: ExternalCursor | None = None
