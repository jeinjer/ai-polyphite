from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from predictionlab.providers.base import (
    FetchMarketsRequest,
    ProviderMarket,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
)


def test_provider_market_normalizes_external_values() -> None:
    market = ProviderMarket(
        provider_market_id="  external-1  ",
        title="  Will this normalize?  ",
        status=ProviderMarketStatus.OPEN,
        source_updated_at=datetime(
            2026,
            7,
            28,
            14,
            tzinfo=timezone(timedelta(hours=2)),
        ),
    )

    assert market.provider_market_id == "external-1"
    assert market.title == "Will this normalize?"
    assert market.source_updated_at == datetime(2026, 7, 28, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("probability", Decimal("1.01")),
        ("yes_price", Decimal("-0.01")),
        ("volume", Decimal("-1")),
        ("liquidity", Decimal("NaN")),
    ],
)
def test_provider_snapshot_rejects_invalid_numbers(
    field: str,
    value: Decimal,
) -> None:
    values = {
        "provider_market_id": "external-1",
        "observed_at": datetime(2026, 7, 28, tzinfo=UTC),
        field: value,
    }

    with pytest.raises(ValidationError):
        ProviderMarketSnapshot.model_validate(values)


def test_provider_dtos_reject_naive_datetimes_and_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        FetchMarketsRequest(updated_after=datetime(2026, 7, 28))

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProviderMarket.model_validate(
            {
                "provider_market_id": "external-1",
                "title": "Market",
                "status": "open",
                "provider_specific_payload": {},
            }
        )
