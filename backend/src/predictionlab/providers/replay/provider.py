"""Deterministic local historical provider with an explicit lookahead barrier."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from predictionlab.core.clock import ReplayClock
from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    MarketDataProvider,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealthStatus,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderResolutionOutcome,
    SnapshotBatch,
)
from predictionlab.providers.replay.dataset import (
    ReplayDatasetMetadata,
    ReplayMarketRecord,
    load_replay_dataset,
)
from predictionlab.providers.replay.errors import ReplayDatasetFormatError

_CURSOR_PREFIX = "replay:"
_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ReplayProvider(MarketDataProvider):
    """Expose only dataset facts available at the simulated instant."""

    def __init__(
        self,
        dataset_path: Path,
        *,
        clock: ReplayClock | None = None,
        code: str = "replay",
    ) -> None:
        self._dataset = load_replay_dataset(dataset_path)
        self._replay_clock = clock or ReplayClock(
            start_at=self._dataset.metadata.replay_start,
            event_times=self._dataset.event_times,
        )
        if self._replay_clock.start_at < self._dataset.metadata.replay_start:
            raise ReplayDatasetFormatError("ReplayClock starts before the dataset range.")
        super().__init__(clock=self._replay_clock)
        if not _PROVIDER_CODE_PATTERN.fullmatch(code):
            raise ValueError("Invalid ReplayProvider code.")
        self._code = code
        self._markets = {
            record.provider_market_id: record for record in self._dataset.markets
        }

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return f"Replay: {self._dataset.metadata.dataset_id} v{self._dataset.metadata.version}"

    @property
    def metadata(self) -> ReplayDatasetMetadata:
        """Safe manifest only; event records remain private."""

        return self._dataset.metadata

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities.of(
            ProviderCapability.MARKET_LISTING,
            ProviderCapability.MARKET_DETAIL,
            ProviderCapability.LATEST_OBSERVATION,
            ProviderCapability.INCREMENTAL_MARKETS,
        )

    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        self.capabilities.require(ProviderCapability.MARKET_LISTING)
        visible = sorted(self._visible_markets(), key=lambda item: item.provider_market_id)
        if request.statuses:
            visible = [market for market in visible if market.status in request.statuses]
        if request.updated_after is not None:
            visible = [
                market
                for market in visible
                if market.source_updated_at is not None
                and market.source_updated_at > request.updated_after
            ]
        offset = self._decode_cursor(request.cursor)
        page = tuple(visible[offset : offset + request.limit])
        next_offset = offset + len(page)
        next_cursor = (
            f"{_CURSOR_PREFIX}{next_offset}" if next_offset < len(visible) else None
        )
        return MarketBatch(markets=page, next_cursor=next_cursor)

    async def fetch_market(self, provider_market_id: str) -> ProviderMarket | None:
        self.capabilities.require(ProviderCapability.MARKET_DETAIL)
        record = self._markets.get(provider_market_id)
        if record is None or record.available_at > self._now():
            return None
        return self._market_as_of(record, self._now())

    async def fetch_latest_observation(
        self,
        provider_market_id: str,
    ) -> ProviderMarketObservation | None:
        self.capabilities.require(ProviderCapability.LATEST_OBSERVATION)
        market = self._markets.get(provider_market_id)
        if market is None or market.available_at > self._now():
            return None
        visible = [
            item
            for item in self._dataset.observations
            if item.provider_market_id == provider_market_id
            and item.observed_at <= self._now()
        ]
        if not visible:
            return None
        latest = max(visible, key=lambda item: item.observed_at)
        return ProviderMarketObservation(
            provider_market_id=latest.provider_market_id,
            observed_at=latest.observed_at,
            probability=latest.probability,
            volume=latest.volume,
            liquidity=latest.liquidity,
            source_updated_at=latest.source_updated_at,
            raw_payload_hash=latest.raw_payload_hash,
        )

    async def fetch_latest_snapshot(
        self,
        provider_market_id: str,
    ) -> ProviderMarketSnapshot | None:
        del provider_market_id
        self.capabilities.require(ProviderCapability.LATEST_SNAPSHOT)
        return None

    async def fetch_snapshots(
        self,
        request: FetchSnapshotsRequest,
    ) -> SnapshotBatch:
        del request
        self.capabilities.require(ProviderCapability.HISTORICAL_SNAPSHOTS)
        return SnapshotBatch(snapshots=())

    async def _probe_health(self) -> ProviderHealthStatus:
        return ProviderHealthStatus.HEALTHY

    def _visible_markets(self) -> list[ProviderMarket]:
        now = self._now()
        return [
            self._market_as_of(record, now)
            for record in self._markets.values()
            if record.available_at <= now
        ]

    def _market_as_of(
        self,
        record: ReplayMarketRecord,
        as_of: datetime,
    ) -> ProviderMarket:
        status = ProviderMarketStatus(record.initial_status)
        outcome = ProviderResolutionOutcome.UNRESOLVED
        resolved_at: datetime | None = None
        resolution_source: str | None = None
        update_times = [record.available_at]

        states = sorted(
            (
                item
                for item in self._dataset.state_changes
                if item.provider_market_id == record.provider_market_id
                and item.occurred_at <= as_of
            ),
            key=lambda item: item.occurred_at,
        )
        for state in states:
            status = ProviderMarketStatus(state.status)
            update_times.append(state.occurred_at)

        observations = [
            item
            for item in self._dataset.observations
            if item.provider_market_id == record.provider_market_id
            and item.observed_at <= as_of
        ]
        update_times.extend(item.observed_at for item in observations)

        resolutions = [
            item
            for item in self._dataset.resolutions
            if item.provider_market_id == record.provider_market_id
            and item.occurred_at <= as_of
        ]
        if resolutions:
            resolution = max(resolutions, key=lambda item: item.occurred_at)
            outcome = ProviderResolutionOutcome(resolution.outcome)
            status = (
                ProviderMarketStatus.CANCELLED
                if outcome is ProviderResolutionOutcome.CANCELLED
                else ProviderMarketStatus.RESOLVED
            )
            resolved_at = resolution.occurred_at
            resolution_source = resolution.source
            update_times.append(resolution.occurred_at)

        return ProviderMarket(
            provider_market_id=record.provider_market_id,
            title=record.title,
            description=record.description,
            category=record.category,
            status=status,
            resolution_at=record.resolution_at,
            source_created_at=record.available_at,
            source_updated_at=max(update_times),
            resolution_outcome=outcome,
            resolved_at=resolved_at,
            resolution_source=resolution_source,
        )

    def _now(self) -> datetime:
        return self._replay_clock.now()

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        if not cursor.startswith(_CURSOR_PREFIX):
            raise ReplayDatasetFormatError("Invalid ReplayProvider cursor.")
        try:
            offset = int(cursor.removeprefix(_CURSOR_PREFIX))
        except ValueError as exc:
            raise ReplayDatasetFormatError("Invalid ReplayProvider cursor.") from exc
        if offset < 0:
            raise ReplayDatasetFormatError("Invalid ReplayProvider cursor.")
        return offset
