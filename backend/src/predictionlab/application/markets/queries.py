from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from predictionlab.domain.markets import MarketStatus, ResolutionOutcome


class MarketOrderField(StrEnum):
    UPDATED_AT = "updated_at"
    INGESTED_AT = "ingested_at"
    RESOLUTION_AT = "resolution_at"
    TITLE = "title"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True, kw_only=True)
class ListMarkets:
    page: int = 1
    page_size: int = 20
    status: MarketStatus | None = None
    provider_code: str | None = None
    category: str | None = None
    order_by: MarketOrderField = MarketOrderField.UPDATED_AT
    direction: SortDirection = SortDirection.DESC

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be positive")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        for field_name in ("provider_code", "category"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} cannot be blank")


@dataclass(frozen=True, slots=True)
class ProviderSummary:
    provider_id: UUID
    code: str
    name: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class SnapshotSummary:
    snapshot_id: UUID
    observed_at: datetime
    yes_price: Decimal
    no_price: Decimal
    probability: Decimal
    spread: Decimal
    volume: Decimal
    liquidity: Decimal


@dataclass(frozen=True, slots=True)
class ObservationSummary:
    observation_id: UUID
    observed_at: datetime
    probability: Decimal | None
    volume: Decimal | None
    liquidity: Decimal | None
    source_updated_at: datetime | None
    ingested_at: datetime
    provider_code: str


@dataclass(frozen=True, slots=True)
class MarketSummary:
    market_id: UUID
    provider_market_id: str
    title: str
    category: str | None
    resolution_at: datetime | None
    source_created_at: datetime | None
    status: MarketStatus
    ingested_at: datetime
    updated_at: datetime
    provider: ProviderSummary
    latest_snapshot: SnapshotSummary | None
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: str | None = None
    latest_observation: ObservationSummary | None = None
    probability_change: Decimal | None = None


@dataclass(frozen=True, slots=True)
class MarketDetail:
    market_id: UUID
    provider_market_id: str
    title: str
    description: str | None
    category: str | None
    resolution_at: datetime | None
    source_created_at: datetime | None
    status: MarketStatus
    ingested_at: datetime
    updated_at: datetime
    provider: ProviderSummary
    latest_snapshot: SnapshotSummary | None
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: str | None = None
    latest_observation: ObservationSummary | None = None
    probability_change: Decimal | None = None


@dataclass(frozen=True, slots=True)
class MarketPage:
    items: tuple[MarketSummary, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True, kw_only=True)
class ListMarketObservations:
    market_id: UUID
    page: int = 1
    page_size: int = 100
    observed_from: datetime | None = None
    observed_to: datetime | None = None

    def __post_init__(self) -> None:
        _validate_history_page(self.page, self.page_size)
        if (
            self.observed_from is not None
            and self.observed_to is not None
            and self.observed_from > self.observed_to
        ):
            raise ValueError("observed_from cannot be after observed_to")


@dataclass(frozen=True, slots=True)
class MarketObservationPage:
    items: tuple[ObservationSummary, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class MarketHistoryEventType(StrEnum):
    SOURCE_CREATED = "source_created"
    INGESTED = "ingested"
    STATE_CHANGED = "state_changed"
    OBSERVATION = "observation"
    SCHEDULED_CLOSE = "scheduled_close"
    RESOLUTION = "resolution"


@dataclass(frozen=True, slots=True)
class MarketHistoryEvent:
    event_id: str
    event_type: MarketHistoryEventType
    occurred_at: datetime
    previous_status: MarketStatus | None = None
    status: MarketStatus | None = None
    resolution_outcome: ResolutionOutcome | None = None
    probability: Decimal | None = None
    volume: Decimal | None = None
    liquidity: Decimal | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ListMarketHistory:
    market_id: UUID
    page: int = 1
    page_size: int = 100

    def __post_init__(self) -> None:
        _validate_history_page(self.page, self.page_size)


@dataclass(frozen=True, slots=True)
class MarketHistoryPage:
    items: tuple[MarketHistoryEvent, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


def _validate_history_page(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be positive")
    if not 1 <= page_size <= 500:
        raise ValueError("page_size must be between 1 and 500")
