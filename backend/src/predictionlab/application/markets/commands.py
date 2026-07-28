from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from predictionlab.domain.markets import MarketStatus, ResolutionOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateProvider:
    code: str
    name: str
    enabled: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateProvider:
    provider_id: UUID
    name: str
    enabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SynchronizeProvider:
    code: str
    name: str
    enabled: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateMarket:
    provider_id: UUID
    provider_market_id: str
    title: str
    status: MarketStatus
    description: str | None = None
    category: str | None = None
    resolution_at: datetime | None = None
    source_created_at: datetime | None = None
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateMarket:
    market_id: UUID
    title: str
    status: MarketStatus
    description: str | None
    category: str | None
    resolution_at: datetime | None
    source_created_at: datetime | None
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SynchronizeMarket:
    provider_id: UUID
    provider_market_id: str
    title: str
    status: MarketStatus
    description: str | None = None
    category: str | None = None
    resolution_at: datetime | None = None
    source_created_at: datetime | None = None
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordMarketSnapshot:
    market_id: UUID
    observed_at: datetime
    yes_price: Decimal
    no_price: Decimal
    probability: Decimal
    spread: Decimal
    volume: Decimal
    liquidity: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordMarketObservation:
    market_id: UUID
    observed_at: datetime
    provider_code: str
    probability: Decimal | None = None
    volume: Decimal | None = None
    liquidity: Decimal | None = None
    source_updated_at: datetime | None = None
    raw_payload_hash: str | None = None
