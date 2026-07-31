from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from predictionlab.core.clock import SystemClock


class MarketInvariantError(ValueError):
    """Raised when market-domain data violates a business invariant."""


class MarketResolutionConflictError(MarketInvariantError):
    """Raised when a provider attempts to rewrite a confirmed resolution."""


class MarketStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ResolutionOutcome(StrEnum):
    UNRESOLVED = "unresolved"
    YES = "yes"
    NO = "no"
    CANCELLED = "cancelled"
    OTHER = "other"


_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_ALLOWED_STATUS_TRANSITIONS: dict[MarketStatus, frozenset[MarketStatus]] = {
    MarketStatus.OPEN: frozenset({MarketStatus.CLOSED, MarketStatus.CANCELLED}),
    MarketStatus.CLOSED: frozenset(
        {MarketStatus.OPEN, MarketStatus.RESOLVED, MarketStatus.CANCELLED}
    ),
    MarketStatus.RESOLVED: frozenset(),
    MarketStatus.CANCELLED: frozenset(),
}


def utc_now() -> datetime:
    return SystemClock().now()


@dataclass(frozen=True, slots=True, kw_only=True)
class Provider:
    code: str
    name: str
    enabled: bool = True
    provider_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _validate_uuid(self.provider_id, "provider_id")
        if not _PROVIDER_CODE_PATTERN.fullmatch(self.code):
            raise MarketInvariantError(
                "code must be lowercase and contain only letters, digits, '_' or '-'"
            )
        object.__setattr__(self, "name", _required_text(self.name, "name", max_length=200))
        if not isinstance(self.enabled, bool):
            raise MarketInvariantError("enabled must be a boolean")

        created_at = _utc_timestamp(self.created_at, "created_at")
        updated_at = _utc_timestamp(self.updated_at, "updated_at")
        _validate_timestamp_order(created_at, updated_at)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def update(
        self,
        *,
        name: str,
        enabled: bool,
        changed_at: datetime,
    ) -> Provider:
        normalized_name = _required_text(name, "name", max_length=200)
        if not isinstance(enabled, bool):
            raise MarketInvariantError("enabled must be a boolean")
        if normalized_name == self.name and enabled is self.enabled:
            return self

        normalized_changed_at = _changed_at(changed_at, self.updated_at)
        return replace(
            self,
            name=normalized_name,
            enabled=enabled,
            updated_at=normalized_changed_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Market:
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
    market_id: UUID = field(default_factory=uuid4)
    ingested_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _validate_uuid(self.market_id, "market_id")
        _validate_uuid(self.provider_id, "provider_id")
        object.__setattr__(
            self,
            "provider_market_id",
            _required_text(
                self.provider_market_id,
                "provider_market_id",
                max_length=512,
            ),
        )
        object.__setattr__(
            self,
            "title",
            _required_text(self.title, "title", max_length=1_000),
        )
        object.__setattr__(
            self,
            "description",
            _optional_text(self.description, "description", max_length=20_000),
        )
        object.__setattr__(
            self,
            "category",
            _optional_text(self.category, "category", max_length=200),
        )
        if not isinstance(self.status, MarketStatus):
            raise MarketInvariantError("status must be a MarketStatus")
        if not isinstance(self.resolution_outcome, ResolutionOutcome):
            raise MarketInvariantError("resolution_outcome must be a ResolutionOutcome")
        if (
            self.status is MarketStatus.RESOLVED
            and self.resolution_outcome is ResolutionOutcome.UNRESOLVED
        ):
            object.__setattr__(
                self,
                "resolution_outcome",
                ResolutionOutcome.OTHER,
            )
        elif (
            self.status is MarketStatus.CANCELLED
            and self.resolution_outcome is ResolutionOutcome.UNRESOLVED
        ):
            object.__setattr__(
                self,
                "resolution_outcome",
                ResolutionOutcome.CANCELLED,
            )

        ingested_at = _utc_timestamp(self.ingested_at, "ingested_at")
        updated_at = _utc_timestamp(self.updated_at, "updated_at")
        _validate_timestamp_order(
            ingested_at,
            updated_at,
            start_field_name="ingested_at",
        )
        object.__setattr__(self, "ingested_at", ingested_at)
        object.__setattr__(self, "updated_at", updated_at)

        if self.source_created_at is not None:
            object.__setattr__(
                self,
                "source_created_at",
                _utc_timestamp(self.source_created_at, "source_created_at"),
            )
        if self.resolution_at is not None:
            object.__setattr__(
                self,
                "resolution_at",
                _utc_timestamp(self.resolution_at, "resolution_at"),
            )
        if self.resolved_at is not None:
            object.__setattr__(
                self,
                "resolved_at",
                _utc_timestamp(self.resolved_at, "resolved_at"),
            )
        object.__setattr__(
            self,
            "resolution_source",
            _optional_text(
                self.resolution_source,
                "resolution_source",
                max_length=200,
            ),
        )
        _validate_resolution_state(
            self.status,
            self.resolution_outcome,
            self.resolved_at,
            self.resolution_source,
        )

    def transition_to(self, status: MarketStatus, *, changed_at: datetime) -> Market:
        if not isinstance(status, MarketStatus):
            raise MarketInvariantError("status must be a MarketStatus")
        if status is self.status:
            return self
        if status not in _ALLOWED_STATUS_TRANSITIONS[self.status]:
            raise MarketInvariantError(
                f"invalid market status transition: {self.status.value} -> {status.value}"
            )

        normalized_changed_at = _changed_at(changed_at, self.updated_at)
        return replace(self, status=status, updated_at=normalized_changed_at)

    def update_details(
        self,
        *,
        title: str,
        description: str | None,
        category: str | None,
        resolution_at: datetime | None,
        source_created_at: datetime | None,
        changed_at: datetime,
    ) -> Market:
        normalized_title = _required_text(title, "title", max_length=1_000)
        normalized_description = _optional_text(
            description,
            "description",
            max_length=20_000,
        )
        normalized_category = _optional_text(
            category,
            "category",
            max_length=200,
        )
        normalized_resolution_at = (
            _utc_timestamp(resolution_at, "resolution_at") if resolution_at is not None else None
        )
        normalized_source_created_at = (
            _utc_timestamp(source_created_at, "source_created_at")
            if source_created_at is not None
            else None
        )
        if (
            normalized_title == self.title
            and normalized_description == self.description
            and normalized_category == self.category
            and normalized_resolution_at == self.resolution_at
            and normalized_source_created_at == self.source_created_at
        ):
            return self

        normalized_changed_at = _changed_at(changed_at, self.updated_at)
        return replace(
            self,
            title=normalized_title,
            description=normalized_description,
            category=normalized_category,
            resolution_at=normalized_resolution_at,
            source_created_at=normalized_source_created_at,
            updated_at=normalized_changed_at,
        )

    def apply_resolution(
        self,
        *,
        outcome: ResolutionOutcome,
        resolved_at: datetime | None,
        source: str | None,
        changed_at: datetime,
    ) -> Market:
        if not isinstance(outcome, ResolutionOutcome):
            raise MarketInvariantError("outcome must be a ResolutionOutcome")
        if outcome is ResolutionOutcome.UNRESOLVED:
            if self.resolution_outcome is ResolutionOutcome.UNRESOLVED:
                return self
            raise MarketResolutionConflictError("a confirmed resolution is terminal")

        normalized_resolved_at = (
            _utc_timestamp(resolved_at, "resolved_at") if resolved_at is not None else None
        )
        normalized_source = _optional_text(
            source,
            "resolution_source",
            max_length=200,
        )
        if self.resolution_outcome is not ResolutionOutcome.UNRESOLVED:
            if _is_legacy_ambiguous_resolution(self):
                target_status = (
                    MarketStatus.CANCELLED
                    if outcome is ResolutionOutcome.CANCELLED
                    else MarketStatus.RESOLVED
                )
                return replace(
                    self,
                    status=target_status,
                    resolution_outcome=outcome,
                    resolved_at=normalized_resolved_at,
                    resolution_source=normalized_source,
                    updated_at=_changed_at(changed_at, self.updated_at),
                )
            if self.resolution_outcome is not outcome:
                raise MarketResolutionConflictError(
                    "a confirmed resolution cannot be overwritten"
                )
            merged_resolved_at = _merge_confirmed_value(
                self.resolved_at,
                normalized_resolved_at,
                "resolved_at",
            )
            merged_source = _merge_confirmed_value(
                self.resolution_source,
                normalized_source,
                "resolution_source",
            )
            if merged_resolved_at == self.resolved_at and merged_source == self.resolution_source:
                return self
            return replace(
                self,
                resolved_at=merged_resolved_at,
                resolution_source=merged_source,
                updated_at=_changed_at(changed_at, self.updated_at),
            )

        target_status = (
            MarketStatus.CANCELLED
            if outcome is ResolutionOutcome.CANCELLED
            else MarketStatus.RESOLVED
        )
        updated = self
        if updated.status is MarketStatus.OPEN and target_status is MarketStatus.RESOLVED:
            updated = updated.transition_to(
                MarketStatus.CLOSED,
                changed_at=changed_at,
            )
        updated = updated.transition_to(target_status, changed_at=changed_at)
        return replace(
            updated,
            resolution_outcome=outcome,
            resolved_at=normalized_resolved_at,
            resolution_source=normalized_source,
        )

    def validate_observation(self, observation: MarketObservation) -> None:
        if observation.market_id != self.market_id:
            raise MarketInvariantError("observation belongs to a different market")
        if self.source_created_at is not None and observation.observed_at < self.source_created_at:
            raise MarketInvariantError("observation cannot predate the external market")

    def validate_snapshot(self, snapshot: MarketSnapshot) -> None:
        if snapshot.market_id != self.market_id:
            raise MarketInvariantError("snapshot belongs to a different market")
        if self.source_created_at is not None and snapshot.observed_at < self.source_created_at:
            raise MarketInvariantError("snapshot cannot predate the external market")


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketSnapshot:
    market_id: UUID
    observed_at: datetime
    yes_price: Decimal
    no_price: Decimal
    probability: Decimal
    spread: Decimal
    volume: Decimal
    liquidity: Decimal
    snapshot_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        _validate_uuid(self.snapshot_id, "snapshot_id")
        _validate_uuid(self.market_id, "market_id")
        object.__setattr__(
            self,
            "observed_at",
            _utc_timestamp(self.observed_at, "observed_at"),
        )
        for field_name in ("yes_price", "no_price", "probability", "spread"):
            _bounded_decimal(getattr(self, field_name), field_name)
        for field_name in ("volume", "liquidity"):
            _non_negative_decimal(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketObservation:
    market_id: UUID
    observed_at: datetime
    provider_code: str
    ingested_at: datetime
    probability: Decimal | None = None
    volume: Decimal | None = None
    liquidity: Decimal | None = None
    source_updated_at: datetime | None = None
    raw_payload_hash: str | None = None
    observation_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        _validate_uuid(self.observation_id, "observation_id")
        _validate_uuid(self.market_id, "market_id")
        if not _PROVIDER_CODE_PATTERN.fullmatch(self.provider_code):
            raise MarketInvariantError("invalid observation provider_code")
        object.__setattr__(
            self,
            "observed_at",
            _utc_timestamp(self.observed_at, "observed_at"),
        )
        object.__setattr__(
            self,
            "ingested_at",
            _utc_timestamp(self.ingested_at, "ingested_at"),
        )
        if self.source_updated_at is not None:
            object.__setattr__(
                self,
                "source_updated_at",
                _utc_timestamp(self.source_updated_at, "source_updated_at"),
            )
        if self.probability is not None:
            _bounded_decimal(self.probability, "probability")
        for field_name in ("volume", "liquidity"):
            value = getattr(self, field_name)
            if value is not None:
                _non_negative_decimal(value, field_name)
        if all(value is None for value in (self.probability, self.volume, self.liquidity)):
            raise MarketInvariantError("observation must contain probability, volume or liquidity")
        if self.raw_payload_hash is not None and not re.fullmatch(
            r"[0-9a-f]{64}",
            self.raw_payload_hash,
        ):
            raise MarketInvariantError("raw_payload_hash must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketStateChange:
    market_id: UUID
    occurred_at: datetime
    status: MarketStatus
    resolution_outcome: ResolutionOutcome
    previous_status: MarketStatus | None = None
    previous_resolution_outcome: ResolutionOutcome | None = None
    resolved_at: datetime | None = None
    resolution_source: str | None = None
    change_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        _validate_uuid(self.change_id, "change_id")
        _validate_uuid(self.market_id, "market_id")
        object.__setattr__(
            self,
            "occurred_at",
            _utc_timestamp(self.occurred_at, "occurred_at"),
        )
        if self.resolved_at is not None:
            object.__setattr__(
                self,
                "resolved_at",
                _utc_timestamp(self.resolved_at, "resolved_at"),
            )
        object.__setattr__(
            self,
            "resolution_source",
            _optional_text(
                self.resolution_source,
                "resolution_source",
                max_length=200,
            ),
        )
        _validate_resolution_state(
            self.status,
            self.resolution_outcome,
            self.resolved_at,
            self.resolution_source,
        )


def _validate_uuid(value: UUID, field_name: str) -> None:
    if not isinstance(value, UUID) or value.int == 0:
        raise MarketInvariantError(f"{field_name} must be a non-zero UUID")


def _required_text(value: str, field_name: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise MarketInvariantError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise MarketInvariantError(f"{field_name} cannot be blank")
    if len(normalized) > max_length:
        raise MarketInvariantError(f"{field_name} cannot exceed {max_length} characters")
    return normalized


def _optional_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int,
) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name, max_length=max_length)


def _utc_timestamp(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise MarketInvariantError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _validate_timestamp_order(
    start_at: datetime,
    updated_at: datetime,
    *,
    start_field_name: str = "created_at",
) -> None:
    if updated_at < start_at:
        raise MarketInvariantError(f"updated_at cannot be before {start_field_name}")


def _changed_at(value: datetime, current_updated_at: datetime) -> datetime:
    normalized = _utc_timestamp(value, "changed_at")
    if normalized < current_updated_at:
        raise MarketInvariantError("changed_at cannot be before updated_at")
    return normalized


def _bounded_decimal(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if value < Decimal("0") or value > Decimal("1"):
        raise MarketInvariantError(f"{field_name} must be between 0 and 1")


def _non_negative_decimal(value: Decimal, field_name: str) -> None:
    _decimal(value, field_name)
    if value < Decimal("0"):
        raise MarketInvariantError(f"{field_name} cannot be negative")


def _decimal(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise MarketInvariantError(f"{field_name} must be a finite Decimal")


def _validate_resolution_state(
    status: MarketStatus,
    outcome: ResolutionOutcome,
    resolved_at: datetime | None,
    resolution_source: str | None,
) -> None:
    if status in {MarketStatus.OPEN, MarketStatus.CLOSED}:
        if outcome is not ResolutionOutcome.UNRESOLVED:
            raise MarketInvariantError("an unresolved market must have outcome unresolved")
        if resolved_at is not None or resolution_source is not None:
            raise MarketInvariantError("an unresolved market cannot contain resolution metadata")
        return
    if status is MarketStatus.CANCELLED:
        if outcome is not ResolutionOutcome.CANCELLED:
            raise MarketInvariantError("a cancelled market must have outcome cancelled")
        return
    if outcome not in {
        ResolutionOutcome.YES,
        ResolutionOutcome.NO,
        ResolutionOutcome.OTHER,
    }:
        raise MarketInvariantError("a resolved market must have outcome yes, no or other")


def _merge_confirmed_value[T](
    current: T | None,
    incoming: T | None,
    field_name: str,
) -> T | None:
    if incoming is None:
        return current
    if current is not None and current != incoming:
        raise MarketResolutionConflictError(
            f"confirmed {field_name} cannot be overwritten"
        )
    return incoming


def _is_legacy_ambiguous_resolution(market: Market) -> bool:
    return (
        market.status is MarketStatus.RESOLVED
        and market.resolution_outcome is ResolutionOutcome.OTHER
        and market.resolved_at is None
        and market.resolution_source is None
    )
