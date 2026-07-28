"""In-memory, deterministic implementation of the Provider SDK."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite

from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    MarketDataProvider,
    ProviderCapabilities,
    ProviderCapability,
    ProviderError,
    ProviderHealthStatus,
    ProviderMarket,
    ProviderMarketNotFoundError,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderResolutionOutcome,
    ProviderUnavailableError,
    SnapshotBatch,
)

_CURSOR_PREFIX = "mock:"
_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class MockProvider(MarketDataProvider):
    """Fully local provider with stable fixtures and realistic behavior."""

    def __init__(
        self,
        *,
        markets: Iterable[ProviderMarket] | None = None,
        snapshots: Mapping[str, Iterable[ProviderMarketSnapshot]] | None = None,
        available: bool = True,
        latency_seconds: float = 0,
        code: str = "mock",
        name: str = "AI-Polyphite Mock Provider",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(clock=clock)
        if not isfinite(latency_seconds) or latency_seconds < 0:
            raise ValueError("latency_seconds must be finite and non-negative.")
        if not _PROVIDER_CODE_PATTERN.fullmatch(code):
            raise ValueError("Invalid MockProvider code.")
        if not name.strip():
            raise ValueError("MockProvider name cannot be blank.")

        market_values = tuple(markets) if markets is not None else _default_markets()
        self._markets = {market.provider_market_id: market for market in market_values}
        if len(self._markets) != len(market_values):
            raise ValueError("MockProvider market IDs must be unique.")

        snapshot_values = snapshots if snapshots is not None else _default_snapshots()
        self._snapshots = self._normalize_snapshots(snapshot_values)
        self._available = available
        self._latency_seconds = latency_seconds
        self._code = code
        self._name = name.strip()

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities.of(*ProviderCapability)

    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        await self._prepare_request(ProviderCapability.MARKET_LISTING)
        markets = sorted(
            self._markets.values(),
            key=lambda item: item.provider_market_id,
        )
        if request.statuses:
            markets = [market for market in markets if market.status in request.statuses]
        if request.updated_after is not None:
            markets = [
                market
                for market in markets
                if market.source_updated_at is not None
                and market.source_updated_at > request.updated_after
            ]

        offset = self._decode_cursor(request.cursor)
        page = tuple(markets[offset : offset + request.limit])
        next_offset = offset + len(page)
        next_cursor = self._encode_cursor(next_offset) if next_offset < len(markets) else None
        return MarketBatch(markets=page, next_cursor=next_cursor)

    async def fetch_market(self, provider_market_id: str) -> ProviderMarket | None:
        await self._prepare_request(ProviderCapability.MARKET_DETAIL)
        return self._markets.get(provider_market_id)

    async def fetch_latest_snapshot(
        self,
        provider_market_id: str,
    ) -> ProviderMarketSnapshot | None:
        await self._prepare_request(ProviderCapability.LATEST_SNAPSHOT)
        self._require_market(provider_market_id)
        snapshots = self._snapshots.get(provider_market_id, ())
        return snapshots[-1] if snapshots else None

    async def fetch_latest_observation(
        self,
        provider_market_id: str,
    ) -> ProviderMarketObservation | None:
        await self._prepare_request(ProviderCapability.LATEST_OBSERVATION)
        self._require_market(provider_market_id)
        snapshots = self._snapshots.get(provider_market_id, ())
        if not snapshots:
            return None
        snapshot = snapshots[-1]
        if all(
            value is None
            for value in (
                snapshot.probability,
                snapshot.volume,
                snapshot.liquidity,
            )
        ):
            return None
        market = self._markets[provider_market_id]
        return ProviderMarketObservation(
            provider_market_id=provider_market_id,
            observed_at=snapshot.observed_at,
            probability=snapshot.probability,
            volume=snapshot.volume,
            liquidity=snapshot.liquidity,
            source_updated_at=market.source_updated_at,
        )

    async def fetch_snapshots(
        self,
        request: FetchSnapshotsRequest,
    ) -> SnapshotBatch:
        await self._prepare_request(ProviderCapability.HISTORICAL_SNAPSHOTS)
        self._require_market(request.provider_market_id)
        snapshots = list(self._snapshots.get(request.provider_market_id, ()))
        if request.observed_after is not None:
            snapshots = [
                snapshot for snapshot in snapshots if snapshot.observed_at > request.observed_after
            ]

        offset = self._decode_cursor(request.cursor)
        page = tuple(snapshots[offset : offset + request.limit])
        next_offset = offset + len(page)
        next_cursor = self._encode_cursor(next_offset) if next_offset < len(snapshots) else None
        return SnapshotBatch(snapshots=page, next_cursor=next_cursor)

    async def _probe_health(self) -> ProviderHealthStatus:
        await self._wait()
        self._ensure_available()
        return ProviderHealthStatus.HEALTHY

    async def _prepare_request(self, capability: ProviderCapability) -> None:
        self.capabilities.require(capability)
        await self._wait()
        self._ensure_available()

    async def _wait(self) -> None:
        if self._latency_seconds:
            await asyncio.sleep(self._latency_seconds)

    def _ensure_available(self) -> None:
        if not self._available:
            raise ProviderUnavailableError("MockProvider is configured as unavailable.")

    def _require_market(self, provider_market_id: str) -> None:
        if provider_market_id not in self._markets:
            raise ProviderMarketNotFoundError(f"Mock market '{provider_market_id}' was not found.")

    def _normalize_snapshots(
        self,
        snapshots: Mapping[str, Iterable[ProviderMarketSnapshot]],
    ) -> dict[str, tuple[ProviderMarketSnapshot, ...]]:
        normalized: dict[str, tuple[ProviderMarketSnapshot, ...]] = {}
        for market_id, values in snapshots.items():
            if market_id not in self._markets:
                raise ValueError(f"Snapshots reference unknown mock market '{market_id}'.")
            sorted_values = tuple(sorted(values, key=lambda item: item.observed_at))
            if any(item.provider_market_id != market_id for item in sorted_values):
                raise ValueError("Snapshot map key and provider_market_id must match.")
            normalized[market_id] = sorted_values
        return normalized

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return f"{_CURSOR_PREFIX}{offset}"

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        if not cursor.startswith(_CURSOR_PREFIX):
            raise ProviderError("Invalid MockProvider cursor.")
        try:
            offset = int(cursor.removeprefix(_CURSOR_PREFIX))
        except ValueError as exc:
            raise ProviderError("Invalid MockProvider cursor.") from exc
        if offset < 0:
            raise ProviderError("Invalid MockProvider cursor.")
        return offset


def _default_markets() -> tuple[ProviderMarket, ...]:
    return (
        ProviderMarket(
            provider_market_id="mock-ai-2027",
            title="Will a frontier AI model pass the benchmark before 2027?",
            description="Deterministic development fixture.",
            category="technology",
            status=ProviderMarketStatus.OPEN,
            resolution_at=datetime(2027, 1, 1, tzinfo=UTC),
            source_created_at=datetime(2026, 1, 1, tzinfo=UTC),
            source_updated_at=datetime(2026, 1, 3, tzinfo=UTC),
        ),
        ProviderMarket(
            provider_market_id="mock-energy-q4",
            title="Will renewable energy exceed the mock Q4 target?",
            description="Deterministic development fixture.",
            category="energy",
            status=ProviderMarketStatus.CLOSED,
            resolution_at=datetime(2026, 12, 31, tzinfo=UTC),
            source_created_at=datetime(2026, 1, 2, tzinfo=UTC),
            source_updated_at=datetime(2026, 2, 1, tzinfo=UTC),
        ),
        ProviderMarket(
            provider_market_id="mock-space-launch",
            title="Will the mock space mission launch on schedule?",
            description="Deterministic development fixture.",
            category="science",
            status=ProviderMarketStatus.RESOLVED,
            resolution_at=datetime(2026, 6, 1, tzinfo=UTC),
            source_created_at=datetime(2026, 1, 3, tzinfo=UTC),
            source_updated_at=datetime(2026, 6, 2, tzinfo=UTC),
            resolution_outcome=ProviderResolutionOutcome.YES,
            resolved_at=datetime(2026, 6, 2, tzinfo=UTC),
            resolution_source="mock_fixture",
        ),
    )


def _default_snapshots() -> dict[str, tuple[ProviderMarketSnapshot, ...]]:
    return {
        "mock-ai-2027": (
            _snapshot("mock-ai-2027", datetime(2026, 1, 3, tzinfo=UTC), "0.42"),
            _snapshot("mock-ai-2027", datetime(2026, 1, 4, tzinfo=UTC), "0.46"),
        ),
        "mock-energy-q4": (_snapshot("mock-energy-q4", datetime(2026, 2, 1, tzinfo=UTC), "0.61"),),
        "mock-space-launch": (
            _snapshot(
                "mock-space-launch",
                datetime(2026, 6, 2, tzinfo=UTC),
                "1",
            ),
        ),
    }


def _snapshot(
    market_id: str,
    observed_at: datetime,
    probability: str,
) -> ProviderMarketSnapshot:
    yes_price = Decimal(probability)
    no_price = Decimal("1") - yes_price
    return ProviderMarketSnapshot(
        provider_market_id=market_id,
        observed_at=observed_at,
        yes_price=yes_price,
        no_price=no_price,
        probability=yes_price,
        spread=(Decimal("0.02") if yes_price not in {Decimal("0"), Decimal("1")} else Decimal("0")),
        volume=Decimal("1000"),
        liquidity=Decimal("500"),
    )
