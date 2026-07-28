from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from predictionlab.application.markets.repositories import (
    ObservationWrite,
    SnapshotWrite,
)
from predictionlab.application.markets.services import ServiceDependencies
from predictionlab.collectors import (
    CollectorConfig,
    CollectorRunFailedError,
    CollectorRunStatus,
    LocalProviderCollectionLock,
    MarketDataCollector,
    RetryPolicy,
)
from predictionlab.collectors.models import CollectorCheckpoint
from predictionlab.domain.markets import (
    Market,
    MarketObservation,
    MarketSnapshot,
    MarketStateChange,
    Provider,
)
from predictionlab.providers.base import (
    FetchMarketsRequest,
    MarketBatch,
    ProviderMarket,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderUnavailableError,
)
from predictionlab.providers.mock import MockProvider

NOW = datetime(2025, 12, 31, tzinfo=UTC)


class MemoryState:
    def __init__(self) -> None:
        self.providers: dict[UUID, Provider] = {}
        self.markets: dict[UUID, Market] = {}
        self.snapshots: dict[tuple[UUID, datetime], MarketSnapshot] = {}
        self.observations: dict[tuple[UUID, datetime], MarketObservation] = {}
        self.market_history: list[MarketStateChange] = []


class ProviderRepository:
    def __init__(self, state: MemoryState) -> None:
        self._state = state

    async def add(self, provider: Provider) -> None:
        self._state.providers[provider.provider_id] = provider

    async def update(self, provider: Provider) -> bool:
        if provider.provider_id not in self._state.providers:
            return False
        self._state.providers[provider.provider_id] = provider
        return True

    async def get_by_id(self, provider_id: UUID) -> Provider | None:
        return self._state.providers.get(provider_id)

    async def get_by_code(self, code: str) -> Provider | None:
        return next(
            (provider for provider in self._state.providers.values() if provider.code == code),
            None,
        )


class MarketRepository:
    def __init__(self, state: MemoryState) -> None:
        self._state = state

    async def add(self, market: Market) -> None:
        self._state.markets[market.market_id] = market

    async def update(self, market: Market) -> bool:
        if market.market_id not in self._state.markets:
            return False
        self._state.markets[market.market_id] = market
        return True

    async def get_by_id(self, market_id: UUID) -> Market | None:
        return self._state.markets.get(market_id)

    async def get_by_provider_reference(
        self,
        *,
        provider_id: UUID,
        provider_market_id: str,
    ) -> Market | None:
        return next(
            (
                market
                for market in self._state.markets.values()
                if market.provider_id == provider_id
                and market.provider_market_id == provider_market_id
            ),
            None,
        )


class SnapshotRepository:
    def __init__(self, state: MemoryState) -> None:
        self._state = state

    async def add_if_absent(self, snapshot: MarketSnapshot) -> SnapshotWrite:
        key = (snapshot.market_id, snapshot.observed_at)
        existing = self._state.snapshots.get(key)
        if existing is not None:
            return SnapshotWrite(snapshot=existing, created=False)
        self._state.snapshots[key] = snapshot
        return SnapshotWrite(snapshot=snapshot, created=True)


class ObservationRepository:
    def __init__(self, state: MemoryState) -> None:
        self._state = state

    async def add_if_absent(
        self,
        observation: MarketObservation,
    ) -> ObservationWrite:
        key = (observation.market_id, observation.observed_at)
        existing = self._state.observations.get(key)
        if existing is not None:
            return ObservationWrite(observation=existing, created=False)
        self._state.observations[key] = observation
        return ObservationWrite(observation=observation, created=True)


class MarketHistoryRepository:
    def __init__(self, state: MemoryState) -> None:
        self._state = state

    async def add(self, change: MarketStateChange) -> None:
        self._state.market_history.append(change)


class UnitOfWork:
    def __init__(self, state: MemoryState) -> None:
        self.providers = ProviderRepository(state)
        self.markets = MarketRepository(state)
        self.snapshots = SnapshotRepository(state)
        self.observations = ObservationRepository(state)
        self.market_history = MarketHistoryRepository(state)

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class CheckpointStore:
    def __init__(self) -> None:
        self.current: CollectorCheckpoint | None = None
        self.saved: list[CollectorCheckpoint] = []

    async def get(self, provider_code: str) -> CollectorCheckpoint | None:
        if self.current is not None:
            assert self.current.provider_code == provider_code
        return self.current

    async def save(self, checkpoint: CollectorCheckpoint) -> None:
        self.current = checkpoint
        self.saved.append(checkpoint)


class StuckCursorMockProvider(MockProvider):
    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        del request
        return MarketBatch(markets=(), next_cursor="mock:0")


class FlakyMockProvider(MockProvider):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self._failures = failures

    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        if self._failures:
            self._failures -= 1
            raise ProviderUnavailableError("temporarily unavailable")
        return await super().fetch_markets(request)


def collector(
    provider: MockProvider,
    *,
    state: MemoryState | None = None,
    checkpoints: CheckpointStore | None = None,
    collection_lock: LocalProviderCollectionLock | None = None,
    page_size: int = 2,
    sleep=None,
) -> tuple[MarketDataCollector, MemoryState, CheckpointStore]:
    resolved_state = state or MemoryState()
    resolved_checkpoints = checkpoints or CheckpointStore()
    resolved_lock = collection_lock or LocalProviderCollectionLock()
    dependencies = ServiceDependencies(
        unit_of_work=lambda: UnitOfWork(resolved_state),
        clock=lambda: NOW,
        id_factory=uuid4,
    )

    async def no_sleep(delay: float) -> None:
        del delay

    return (
        MarketDataCollector(
            provider=provider,
            application_dependencies=dependencies,
            checkpoint_store=resolved_checkpoints,
            collection_lock=resolved_lock,
            config=CollectorConfig(page_size=page_size),
            retry_policy=RetryPolicy(
                max_attempts=3,
                base_delay_seconds=0.1,
                max_delay_seconds=1,
                jitter_ratio=0,
            ),
            clock=lambda: NOW,
            sleep=sleep or no_sleep,
            random_source=lambda: 0,
        ),
        resolved_state,
        resolved_checkpoints,
    )


@pytest.mark.asyncio
async def test_collector_ingests_pages_and_reprocesses_incrementally(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service, state, checkpoints = collector(MockProvider())
    caplog.set_level(logging.INFO)

    first = await service.collect(
        correlation_id="collector-correlation",
        causation_id="scheduler-tick",
    )
    second = await service.collect()

    assert first.status is CollectorRunStatus.SUCCEEDED
    assert first.pages == 2
    assert first.markets_fetched == 3
    assert first.markets_created == 3
    assert first.snapshots_created == 3
    assert first.observations_created == 3
    assert first.retries == 0
    assert len(state.providers) == 1
    assert len(state.markets) == 3
    assert len(state.snapshots) == 3
    assert len(state.observations) == 3

    assert second.markets_fetched == 1
    assert second.markets_unchanged == 1
    assert second.snapshots_duplicate == 1
    assert second.observations_duplicate == 1
    assert second.watermark_before == datetime(2026, 6, 2, tzinfo=UTC)
    assert checkpoints.current is not None
    assert checkpoints.current.cursor is None
    assert checkpoints.current.pending_watermark is None
    assert checkpoints.current.watermark == datetime(2026, 6, 2, tzinfo=UTC)
    assert checkpoints.saved[0].cursor == "mock:2"
    assert "collector_run_completed" in {record.message for record in caplog.records}


@pytest.mark.asyncio
async def test_collector_retries_only_transient_provider_failures() -> None:
    service, _, _ = collector(FlakyMockProvider(failures=2))

    result = await service.collect()

    assert result.status is CollectorRunStatus.SUCCEEDED
    assert result.retries == 2
    assert result.markets_created == 3


@pytest.mark.asyncio
async def test_collector_reports_exhausted_retries() -> None:
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    service, _, checkpoints = collector(
        MockProvider(available=False),
        sleep=record_sleep,
    )

    with pytest.raises(CollectorRunFailedError) as error:
        await service.collect()

    assert error.value.retryable is True
    assert error.value.result.status is CollectorRunStatus.FAILED
    assert error.value.result.error_type == "ProviderUnavailableError"
    assert error.value.result.retries == 2
    assert delays == [0.1, 0.2]
    assert checkpoints.saved == []


@pytest.mark.asyncio
async def test_collector_persists_progress_before_protocol_failure() -> None:
    service, _, checkpoints = collector(StuckCursorMockProvider())

    with pytest.raises(CollectorRunFailedError) as error:
        await service.collect()

    assert error.value.retryable is False
    assert error.value.result.error_type == "CollectorProtocolError"
    assert error.value.result.cursor_after == "mock:0"
    assert checkpoints.current is not None
    assert checkpoints.current.cursor == "mock:0"


@pytest.mark.asyncio
async def test_collector_skips_overlapping_run() -> None:
    lock = LocalProviderCollectionLock()
    service, state, _ = collector(MockProvider(), collection_lock=lock)

    async with lock.acquire("mock") as acquired:
        assert acquired is True
        result = await service.collect()

    assert result.status is CollectorRunStatus.SKIPPED_LOCKED
    assert state.providers == {}


@pytest.mark.asyncio
async def test_collector_skips_incomplete_snapshots_without_inventing_values() -> None:
    market = ProviderMarket(
        provider_market_id="incomplete",
        title="Incomplete snapshot market",
        status=ProviderMarketStatus.OPEN,
        source_updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    snapshot = ProviderMarketSnapshot(
        provider_market_id="incomplete",
        observed_at=datetime(2026, 1, 2, tzinfo=UTC),
        probability=Decimal("0.5"),
    )
    provider = MockProvider(
        markets=(market,),
        snapshots={"incomplete": (snapshot,)},
    )
    service, state, _ = collector(provider)

    result = await service.collect()

    assert result.snapshots_fetched == 1
    assert result.snapshots_skipped == 1
    assert result.snapshots_created == 0
    assert state.snapshots == {}
