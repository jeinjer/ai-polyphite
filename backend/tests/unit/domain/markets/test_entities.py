from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from predictionlab.domain.markets import (
    Market,
    MarketInvariantError,
    MarketObservation,
    MarketSnapshot,
    MarketStatus,
    Provider,
    ResolutionOutcome,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def build_market(**overrides: object) -> Market:
    values: dict[str, object] = {
        "provider_id": uuid4(),
        "provider_market_id": "provider-market-1",
        "title": "Will the event happen?",
        "status": MarketStatus.OPEN,
        "ingested_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return Market(**values)  # type: ignore[arg-type]


def build_snapshot(**overrides: object) -> MarketSnapshot:
    values: dict[str, object] = {
        "market_id": uuid4(),
        "observed_at": NOW,
        "yes_price": Decimal("0.61"),
        "no_price": Decimal("0.42"),
        "probability": Decimal("0.60"),
        "spread": Decimal("0.03"),
        "volume": Decimal("1200.50"),
        "liquidity": Decimal("450.25"),
    }
    values.update(overrides)
    return MarketSnapshot(**values)  # type: ignore[arg-type]


def build_observation(**overrides: object) -> MarketObservation:
    values: dict[str, object] = {
        "market_id": uuid4(),
        "observed_at": NOW,
        "provider_code": "provider",
        "ingested_at": NOW + timedelta(seconds=1),
        "probability": Decimal("0.60"),
    }
    values.update(overrides)
    return MarketObservation(**values)  # type: ignore[arg-type]


def test_provider_normalizes_timestamps_and_name() -> None:
    eastern = timezone(timedelta(hours=-4))

    provider = Provider(
        code="research_provider",
        name="  Research Provider  ",
        created_at=datetime(2026, 7, 27, 8, 0, tzinfo=eastern),
        updated_at=datetime(2026, 7, 27, 8, 30, tzinfo=eastern),
    )

    assert provider.name == "Research Provider"
    assert provider.created_at == NOW
    assert provider.created_at.tzinfo is UTC
    assert provider.updated_at == NOW + timedelta(minutes=30)


def test_provider_update_is_immutable_and_idempotent() -> None:
    provider = Provider(
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )

    unchanged = provider.update(name="Provider", enabled=True, changed_at=NOW)
    updated = provider.update(
        name="Updated Provider",
        enabled=False,
        changed_at=NOW + timedelta(minutes=1),
    )

    assert unchanged is provider
    assert provider.enabled is True
    assert updated.name == "Updated Provider"
    assert updated.enabled is False
    assert updated.updated_at == NOW + timedelta(minutes=1)


@pytest.mark.parametrize("code", ["", "Polymarket", "has spaces", "-leading"])
def test_provider_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(MarketInvariantError):
        Provider(code=code, name="Provider")


def test_entities_reject_nil_identifiers_and_naive_timestamps() -> None:
    with pytest.raises(MarketInvariantError, match="non-zero UUID"):
        Provider(
            provider_id=UUID(int=0),
            code="provider",
            name="Provider",
        )

    with pytest.raises(MarketInvariantError, match="timezone-aware"):
        build_market(ingested_at=datetime(2026, 7, 27, 12, 0))


def test_market_status_transition_returns_a_new_entity() -> None:
    market = build_market()
    changed_at = NOW + timedelta(minutes=1)

    closed = market.transition_to(MarketStatus.CLOSED, changed_at=changed_at)
    resolved = closed.transition_to(
        MarketStatus.RESOLVED,
        changed_at=changed_at + timedelta(minutes=1),
    )

    assert market.status is MarketStatus.OPEN
    assert closed.status is MarketStatus.CLOSED
    assert closed.updated_at == changed_at
    assert resolved.status is MarketStatus.RESOLVED


def test_market_details_update_is_immutable() -> None:
    market = build_market(description="Old", category="old")

    updated = market.update_details(
        title="Updated title",
        description=None,
        category="new",
        resolution_at=NOW + timedelta(days=2),
        source_created_at=NOW - timedelta(days=1),
        changed_at=NOW + timedelta(minutes=1),
    )

    assert market.title == "Will the event happen?"
    assert updated.title == "Updated title"
    assert updated.description is None
    assert updated.category == "new"
    assert updated.resolution_at == NOW + timedelta(days=2)
    assert updated.source_created_at == NOW - timedelta(days=1)


def test_updates_cannot_move_time_backwards() -> None:
    provider = Provider(
        code="provider",
        name="Provider",
        created_at=NOW,
        updated_at=NOW,
    )

    with pytest.raises(MarketInvariantError, match="before updated_at"):
        provider.update(
            name="Updated",
            enabled=True,
            changed_at=NOW - timedelta(seconds=1),
        )


@pytest.mark.parametrize(
    ("initial", "target"),
    [
        (MarketStatus.OPEN, MarketStatus.RESOLVED),
        (MarketStatus.RESOLVED, MarketStatus.OPEN),
        (MarketStatus.CANCELLED, MarketStatus.OPEN),
    ],
)
def test_market_rejects_invalid_status_transitions(
    initial: MarketStatus,
    target: MarketStatus,
) -> None:
    market = build_market(status=initial)

    with pytest.raises(MarketInvariantError, match="invalid market status transition"):
        market.transition_to(target, changed_at=NOW + timedelta(minutes=1))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("yes_price", Decimal("-0.01")),
        ("no_price", Decimal("1.01")),
        ("probability", Decimal("NaN")),
        ("spread", Decimal("1.1")),
        ("volume", Decimal("-1")),
        ("liquidity", Decimal("-0.1")),
    ],
)
def test_snapshot_rejects_invalid_numeric_values(
    field_name: str,
    value: Decimal,
) -> None:
    with pytest.raises(MarketInvariantError):
        build_snapshot(**{field_name: value})


def test_snapshot_requires_decimal_values() -> None:
    with pytest.raises(MarketInvariantError, match="finite Decimal"):
        build_snapshot(yes_price=0.5)


def test_yes_and_no_prices_are_not_required_to_sum_to_one() -> None:
    snapshot = build_snapshot(
        yes_price=Decimal("0.61"),
        no_price=Decimal("0.42"),
    )

    assert snapshot.yes_price + snapshot.no_price == Decimal("1.03")


def test_market_validates_snapshot_relationship_and_time() -> None:
    market = build_market(source_created_at=NOW - timedelta(days=1))
    valid_snapshot = build_snapshot(
        market_id=market.market_id,
        observed_at=NOW - timedelta(hours=1),
    )

    market.validate_snapshot(valid_snapshot)

    with pytest.raises(MarketInvariantError, match="different market"):
        market.validate_snapshot(build_snapshot())
    with pytest.raises(MarketInvariantError, match="cannot predate"):
        market.validate_snapshot(
            build_snapshot(
                market_id=market.market_id,
                observed_at=NOW - timedelta(days=1, seconds=1),
            )
        )


def test_market_accepts_historical_snapshot_when_source_creation_is_unknown() -> None:
    market = build_market(ingested_at=NOW)
    historical = build_snapshot(
        market_id=market.market_id,
        observed_at=NOW - timedelta(days=30),
    )

    market.validate_snapshot(historical)


def test_market_observation_keeps_unavailable_metrics_null() -> None:
    observation = build_observation(
        probability=None,
        volume=Decimal("1200.50"),
        liquidity=None,
        source_updated_at=NOW - timedelta(seconds=1),
        raw_payload_hash="a" * 64,
    )

    assert observation.probability is None
    assert observation.volume == Decimal("1200.50")
    assert observation.liquidity is None
    assert observation.raw_payload_hash == "a" * 64


def test_market_observation_requires_one_real_metric() -> None:
    with pytest.raises(MarketInvariantError, match="must contain"):
        build_observation(
            probability=None,
            volume=None,
            liquidity=None,
        )


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        (ResolutionOutcome.YES, MarketStatus.RESOLVED),
        (ResolutionOutcome.NO, MarketStatus.RESOLVED),
        (ResolutionOutcome.CANCELLED, MarketStatus.CANCELLED),
    ],
)
def test_market_applies_explicit_terminal_resolution(
    outcome: ResolutionOutcome,
    expected_status: MarketStatus,
) -> None:
    market = build_market()
    resolved_at = NOW + timedelta(hours=1)

    resolved = market.apply_resolution(
        outcome=outcome,
        resolved_at=resolved_at,
        source="provider_public_api",
        changed_at=resolved_at,
    )

    assert resolved.status is expected_status
    assert resolved.resolution_outcome is outcome
    assert resolved.resolved_at == resolved_at
    assert resolved.resolution_source == "provider_public_api"


def test_confirmed_resolution_cannot_be_overwritten() -> None:
    market = build_market().apply_resolution(
        outcome=ResolutionOutcome.YES,
        resolved_at=NOW + timedelta(hours=1),
        source="provider_public_api",
        changed_at=NOW + timedelta(hours=1),
    )

    with pytest.raises(MarketInvariantError, match="cannot be overwritten"):
        market.apply_resolution(
            outcome=ResolutionOutcome.NO,
            resolved_at=NOW + timedelta(hours=2),
            source="provider_public_api",
            changed_at=NOW + timedelta(hours=2),
        )


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (ResolutionOutcome.YES, MarketStatus.RESOLVED),
        (ResolutionOutcome.NO, MarketStatus.RESOLVED),
        (ResolutionOutcome.CANCELLED, MarketStatus.CANCELLED),
    ],
)
def test_legacy_ambiguous_resolution_accepts_first_real_confirmation(
    outcome: ResolutionOutcome,
    status: MarketStatus,
) -> None:
    legacy_market = build_market(status=MarketStatus.RESOLVED)

    confirmed = legacy_market.apply_resolution(
        outcome=outcome,
        resolved_at=NOW + timedelta(hours=1),
        source="provider_public_api",
        changed_at=NOW + timedelta(hours=1),
    )

    assert confirmed.status is status
    assert confirmed.resolution_outcome is outcome
    assert confirmed.resolution_source == "provider_public_api"


def test_confirmed_non_standard_resolution_is_terminal() -> None:
    market = build_market(
        status=MarketStatus.RESOLVED,
        resolution_outcome=ResolutionOutcome.OTHER,
        resolution_source="provider_public_api",
    )

    with pytest.raises(MarketInvariantError, match="cannot be overwritten"):
        market.apply_resolution(
            outcome=ResolutionOutcome.YES,
            resolved_at=NOW + timedelta(hours=1),
            source="provider_public_api",
            changed_at=NOW + timedelta(hours=1),
        )


def test_scheduled_close_is_not_treated_as_resolution() -> None:
    scheduled_close = NOW + timedelta(days=1)
    market = build_market(resolution_at=scheduled_close)

    assert market.status is MarketStatus.OPEN
    assert market.resolution_outcome is ResolutionOutcome.UNRESOLVED
    assert market.resolved_at is None
