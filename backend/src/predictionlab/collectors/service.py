"""Incremental, at-least-once market-data collection orchestration."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from time import perf_counter
from uuid import UUID, uuid4

from predictionlab.application.markets import (
    MarketObservationService,
    MarketService,
    MarketSnapshotService,
    ProviderService,
    RecordMarketObservation,
    RecordMarketSnapshot,
    ServiceDependencies,
    SynchronizeMarket,
    SynchronizeProvider,
)
from predictionlab.collectors.errors import (
    CollectorProtocolError,
    CollectorRunFailedError,
)
from predictionlab.collectors.models import (
    CollectorCheckpoint,
    CollectorConfig,
    CollectorRunResult,
    CollectorRunStarted,
    CollectorRunStatus,
)
from predictionlab.collectors.ports import (
    CollectorCheckpointStore,
    CollectorRunStore,
    NullCollectorRunStore,
    ProviderCollectionLock,
)
from predictionlab.collectors.retry import (
    AsyncSleep,
    ProviderRetryExecutor,
    RandomSource,
    RetryPolicy,
)
from predictionlab.core.context import (
    bind_request_context,
    get_correlation_id,
    get_trace_id,
    reset_request_context,
)
from predictionlab.domain.markets import (
    Market,
    MarketStatus,
    ResolutionOutcome,
)
from predictionlab.domain.markets.entities import utc_now
from predictionlab.providers.base import (
    FetchMarketsRequest,
    MarketDataProvider,
    ProviderCapability,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    TransientProviderError,
)

logger = logging.getLogger(__name__)

type Clock = Callable[[], datetime]
type RunIdFactory = Callable[[], UUID]


@dataclass(slots=True)
class _Progress:
    pages: int = 0
    markets_fetched: int = 0
    markets_created: int = 0
    markets_updated: int = 0
    markets_unchanged: int = 0
    snapshots_fetched: int = 0
    snapshots_created: int = 0
    snapshots_duplicate: int = 0
    snapshots_skipped: int = 0
    observations_fetched: int = 0
    observations_created: int = 0
    observations_duplicate: int = 0
    observations_skipped: int = 0
    retries: int = 0
    checkpoint: CollectorCheckpoint | None = None

    def record_retry(self) -> None:
        self.retries += 1


class MarketDataCollector:
    """Collect one provider catalog using durable, resumable checkpoints."""

    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        application_dependencies: ServiceDependencies,
        checkpoint_store: CollectorCheckpointStore,
        collection_lock: ProviderCollectionLock,
        run_store: CollectorRunStore | None = None,
        config: CollectorConfig | None = None,
        retry_policy: RetryPolicy | None = None,
        clock: Clock = utc_now,
        run_id_factory: RunIdFactory = uuid4,
        sleep: AsyncSleep = asyncio.sleep,
        random_source: RandomSource = random.random,
    ) -> None:
        self._provider = provider
        self._provider_service = ProviderService(application_dependencies)
        self._market_service = MarketService(application_dependencies)
        self._snapshot_service = MarketSnapshotService(application_dependencies)
        self._observation_service = MarketObservationService(application_dependencies)
        self._checkpoint_store = checkpoint_store
        self._collection_lock = collection_lock
        self._run_store = run_store or NullCollectorRunStore()
        self._config = config or CollectorConfig()
        self._retry = ProviderRetryExecutor(
            retry_policy or RetryPolicy(),
            sleep=sleep,
            random_source=random_source,
        )
        self._clock = clock
        self._run_id_factory = run_id_factory

    async def collect(
        self,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CollectorRunResult:
        run_id = self._run_id_factory()
        resolved_correlation_id = correlation_id or get_correlation_id() or str(run_id)
        trace_id = get_trace_id() or run_id.hex
        started_at = self._now()
        timer = perf_counter()
        tokens = bind_request_context(
            correlation_id=resolved_correlation_id,
            trace_id=trace_id,
        )
        progress = _Progress()
        checkpoint: CollectorCheckpoint | None = None
        checkpoint_before: CollectorCheckpoint | None = None
        context: dict[str, object] = {
            "collector_run_id": str(run_id),
            "provider_code": self._provider.code,
            "causation_id": causation_id,
        }
        logger.info("collector_run_started", extra=context)
        run_started = False

        try:
            await self._run_store.start(
                CollectorRunStarted(
                    run_id=run_id,
                    provider_code=self._provider.code,
                    started_at=started_at,
                    correlation_id=resolved_correlation_id,
                )
            )
            run_started = True
            async with self._collection_lock.acquire(self._provider.code) as acquired:
                if not acquired:
                    result = self._result(
                        run_id=run_id,
                        correlation_id=resolved_correlation_id,
                        causation_id=causation_id,
                        status=CollectorRunStatus.SKIPPED_LOCKED,
                        started_at=started_at,
                        timer=timer,
                        checkpoint=None,
                        checkpoint_before=None,
                        progress=progress,
                    )
                    logger.info(
                        "collector_run_skipped",
                        extra={**context, **_result_log_fields(result)},
                    )
                    await self._run_store.finish(result)
                    return result

                self._provider.capabilities.require(ProviderCapability.MARKET_LISTING)
                provider_sync = await self._provider_service.synchronize(
                    SynchronizeProvider(
                        code=self._provider.code,
                        name=self._provider.name,
                    )
                )
                checkpoint = await self._checkpoint_store.get(self._provider.code)
                if checkpoint is None:
                    checkpoint = CollectorCheckpoint(
                        provider_code=self._provider.code,
                        cursor=None,
                        watermark=None,
                        pending_watermark=None,
                        updated_at=started_at,
                    )
                checkpoint_before = checkpoint

                checkpoint = await self._collect_pages(
                    checkpoint=checkpoint,
                    provider_id=provider_sync.entity.provider_id,
                    progress=progress,
                    log_context=context,
                )
                result = self._result(
                    run_id=run_id,
                    correlation_id=resolved_correlation_id,
                    causation_id=causation_id,
                    status=CollectorRunStatus.SUCCEEDED,
                    started_at=started_at,
                    timer=timer,
                    checkpoint=checkpoint,
                    checkpoint_before=checkpoint_before,
                    progress=progress,
                )
                logger.info(
                    "collector_run_completed",
                    extra={**context, **_result_log_fields(result)},
                )
                await self._run_store.finish(result)
                return result
        except Exception as exc:
            result = self._result(
                run_id=run_id,
                correlation_id=resolved_correlation_id,
                causation_id=causation_id,
                status=CollectorRunStatus.FAILED,
                started_at=started_at,
                timer=timer,
                checkpoint=progress.checkpoint or checkpoint,
                checkpoint_before=checkpoint_before,
                progress=progress,
                error_type=type(exc).__name__,
            )
            logger.error(
                "collector_run_failed",
                extra={**context, **_result_log_fields(result)},
            )
            if run_started:
                await self._run_store.finish(result)
            raise CollectorRunFailedError(
                result,
                retryable=isinstance(exc, TransientProviderError),
            ) from exc
        finally:
            reset_request_context(tokens)

    async def _collect_pages(
        self,
        *,
        checkpoint: CollectorCheckpoint,
        provider_id: UUID,
        progress: _Progress,
        log_context: dict[str, object],
    ) -> CollectorCheckpoint:
        current = checkpoint
        for _ in range(self._config.max_pages_per_run):
            updated_after = self._incremental_start(current.watermark)
            request = FetchMarketsRequest(
                cursor=current.cursor,
                limit=self._config.page_size,
                updated_after=updated_after,
            )
            outcome = await self._retry.execute(
                partial(self._provider.fetch_markets, request),
                operation_name="fetch_markets",
                context=log_context,
                on_retry=progress.record_retry,
            )
            batch = outcome.value
            if batch.next_cursor is not None and batch.next_cursor == current.cursor:
                raise CollectorProtocolError("Provider returned a non-advancing cursor.")

            progress.pages += 1
            progress.markets_fetched += len(batch.markets)
            pending_watermark = _latest_datetime(
                current.watermark,
                current.pending_watermark,
            )
            for external_market in batch.markets:
                market = await self._synchronize_market(
                    provider_id=provider_id,
                    external_market=external_market,
                    progress=progress,
                    log_context=log_context,
                )
                if self._config.collect_latest_observations:
                    await self._collect_observation(
                        market=market,
                        external_market=external_market,
                        progress=progress,
                        log_context=log_context,
                    )
                if self._config.collect_latest_snapshots:
                    await self._collect_snapshot(
                        market=market,
                        external_market=external_market,
                        progress=progress,
                        log_context=log_context,
                    )
                pending_watermark = _latest_datetime(
                    pending_watermark,
                    external_market.source_updated_at,
                )

            current = self._next_checkpoint(
                current=current,
                next_cursor=batch.next_cursor,
                pending_watermark=pending_watermark,
            )
            await self._checkpoint_store.save(current)
            progress.checkpoint = current
            logger.info(
                "collector_page_completed",
                extra={
                    **log_context,
                    "page": progress.pages,
                    "page_markets": len(batch.markets),
                    "next_cursor_present": batch.next_cursor is not None,
                    "watermark": current.watermark,
                },
            )
            if batch.next_cursor is None:
                return current

        raise CollectorProtocolError("Provider exceeded max_pages_per_run.")

    async def _synchronize_market(
        self,
        *,
        provider_id: UUID,
        external_market: ProviderMarket,
        progress: _Progress,
        log_context: dict[str, object],
    ) -> Market:
        synchronized = await self._market_service.synchronize(
            SynchronizeMarket(
                provider_id=provider_id,
                provider_market_id=external_market.provider_market_id,
                title=external_market.title,
                description=external_market.description,
                category=external_market.category,
                resolution_at=external_market.resolution_at,
                source_created_at=external_market.source_created_at,
                status=MarketStatus(external_market.status.value),
                resolution_outcome=ResolutionOutcome(external_market.resolution_outcome.value),
                resolved_at=external_market.resolved_at,
                resolution_source=external_market.resolution_source,
            )
        )
        if synchronized.created:
            progress.markets_created += 1
        elif synchronized.updated:
            progress.markets_updated += 1
        else:
            progress.markets_unchanged += 1
        logger.debug(
            "collector_market_synchronized",
            extra={
                **log_context,
                "provider_market_id": external_market.provider_market_id,
                "market_id": str(synchronized.entity.market_id),
                "created": synchronized.created,
                "updated": synchronized.updated,
            },
        )
        return synchronized.entity

    async def _collect_observation(
        self,
        *,
        market: Market,
        external_market: ProviderMarket,
        progress: _Progress,
        log_context: dict[str, object],
    ) -> None:
        if not self._provider.capabilities.supports(ProviderCapability.LATEST_OBSERVATION):
            return
        outcome = await self._retry.execute(
            partial(
                self._provider.fetch_latest_observation,
                external_market.provider_market_id,
            ),
            operation_name="fetch_latest_observation",
            context=log_context,
            on_retry=progress.record_retry,
        )
        observation = outcome.value
        if observation is None:
            progress.observations_skipped += 1
            return
        progress.observations_fetched += 1
        _validate_observation_reference(observation, market)
        write = await self._observation_service.record(
            RecordMarketObservation(
                market_id=market.market_id,
                observed_at=observation.observed_at,
                provider_code=self._provider.code,
                probability=observation.probability,
                volume=observation.volume,
                liquidity=observation.liquidity,
                source_updated_at=observation.source_updated_at,
                raw_payload_hash=observation.raw_payload_hash,
            )
        )
        if write.created:
            progress.observations_created += 1
        else:
            progress.observations_duplicate += 1

    async def _collect_snapshot(
        self,
        *,
        market: Market,
        external_market: ProviderMarket,
        progress: _Progress,
        log_context: dict[str, object],
    ) -> None:
        if not self._provider.capabilities.supports(ProviderCapability.LATEST_SNAPSHOT):
            return

        outcome = await self._retry.execute(
            partial(
                self._provider.fetch_latest_snapshot,
                external_market.provider_market_id,
            ),
            operation_name="fetch_latest_snapshot",
            context=log_context,
            on_retry=progress.record_retry,
        )
        snapshot = outcome.value
        if snapshot is None:
            return
        progress.snapshots_fetched += 1

        skip_reason = _snapshot_skip_reason(snapshot, market)
        if skip_reason is not None:
            progress.snapshots_skipped += 1
            logger.warning(
                "collector_snapshot_skipped",
                extra={
                    **log_context,
                    "provider_market_id": external_market.provider_market_id,
                    "market_id": str(market.market_id),
                    "reason": skip_reason,
                },
            )
            return

        assert snapshot.yes_price is not None
        assert snapshot.no_price is not None
        assert snapshot.probability is not None
        assert snapshot.spread is not None
        assert snapshot.volume is not None
        assert snapshot.liquidity is not None
        write = await self._snapshot_service.record(
            RecordMarketSnapshot(
                market_id=market.market_id,
                observed_at=snapshot.observed_at,
                yes_price=snapshot.yes_price,
                no_price=snapshot.no_price,
                probability=snapshot.probability,
                spread=snapshot.spread,
                volume=snapshot.volume,
                liquidity=snapshot.liquidity,
            )
        )
        if write.created:
            progress.snapshots_created += 1
        else:
            progress.snapshots_duplicate += 1

    def _incremental_start(self, watermark: datetime | None) -> datetime | None:
        if watermark is None or not self._provider.capabilities.supports(
            ProviderCapability.INCREMENTAL_MARKETS
        ):
            return None
        return watermark - timedelta(seconds=self._config.watermark_overlap_seconds)

    def _next_checkpoint(
        self,
        *,
        current: CollectorCheckpoint,
        next_cursor: str | None,
        pending_watermark: datetime | None,
    ) -> CollectorCheckpoint:
        if next_cursor is None:
            return CollectorCheckpoint(
                provider_code=current.provider_code,
                cursor=None,
                watermark=_latest_datetime(
                    current.watermark,
                    pending_watermark,
                ),
                pending_watermark=None,
                updated_at=self._now(),
            )
        return CollectorCheckpoint(
            provider_code=current.provider_code,
            cursor=next_cursor,
            watermark=current.watermark,
            pending_watermark=pending_watermark,
            updated_at=self._now(),
        )

    def _result(
        self,
        *,
        run_id: UUID,
        correlation_id: str,
        causation_id: str | None,
        status: CollectorRunStatus,
        started_at: datetime,
        timer: float,
        checkpoint: CollectorCheckpoint | None,
        checkpoint_before: CollectorCheckpoint | None,
        progress: _Progress,
        error_type: str | None = None,
    ) -> CollectorRunResult:
        finished_at = self._now()
        return CollectorRunResult(
            run_id=run_id,
            provider_code=self._provider.code,
            correlation_id=correlation_id,
            causation_id=causation_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round((perf_counter() - timer) * 1000, 3),
            cursor_before=(checkpoint_before.cursor if checkpoint_before is not None else None),
            cursor_after=checkpoint.cursor if checkpoint is not None else None,
            watermark_before=(
                checkpoint_before.watermark if checkpoint_before is not None else None
            ),
            watermark_after=checkpoint.watermark if checkpoint is not None else None,
            pages=progress.pages,
            markets_fetched=progress.markets_fetched,
            markets_created=progress.markets_created,
            markets_updated=progress.markets_updated,
            markets_unchanged=progress.markets_unchanged,
            snapshots_fetched=progress.snapshots_fetched,
            snapshots_created=progress.snapshots_created,
            snapshots_duplicate=progress.snapshots_duplicate,
            snapshots_skipped=progress.snapshots_skipped,
            observations_fetched=progress.observations_fetched,
            observations_created=progress.observations_created,
            observations_duplicate=progress.observations_duplicate,
            observations_skipped=progress.observations_skipped,
            retries=progress.retries,
            error_type=error_type,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Collector clock must return a timezone-aware datetime.")
        return value.astimezone(UTC)


def _snapshot_skip_reason(
    snapshot: ProviderMarketSnapshot,
    market: Market,
) -> str | None:
    if snapshot.provider_market_id != market.provider_market_id:
        raise CollectorProtocolError("Snapshot references a different external market.")
    if any(
        value is None
        for value in (
            snapshot.yes_price,
            snapshot.no_price,
            snapshot.probability,
            snapshot.spread,
            snapshot.volume,
            snapshot.liquidity,
        )
    ):
        return "incomplete_snapshot"
    if market.source_created_at is not None and snapshot.observed_at < market.source_created_at:
        raise CollectorProtocolError("Snapshot predates the external market creation timestamp.")
    return None


def _validate_observation_reference(
    observation: ProviderMarketObservation,
    market: Market,
) -> None:
    if observation.provider_market_id != market.provider_market_id:
        raise CollectorProtocolError("Observation references a different external market.")


def _latest_datetime(
    left: datetime | None,
    right: datetime | None,
) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _result_log_fields(result: CollectorRunResult) -> dict[str, object]:
    return {
        "status": result.status.value,
        "duration_ms": result.duration_ms,
        "pages": result.pages,
        "markets_fetched": result.markets_fetched,
        "markets_created": result.markets_created,
        "markets_updated": result.markets_updated,
        "markets_unchanged": result.markets_unchanged,
        "snapshots_fetched": result.snapshots_fetched,
        "snapshots_created": result.snapshots_created,
        "snapshots_duplicate": result.snapshots_duplicate,
        "snapshots_skipped": result.snapshots_skipped,
        "observations_fetched": result.observations_fetched,
        "observations_created": result.observations_created,
        "observations_duplicate": result.observations_duplicate,
        "observations_skipped": result.observations_skipped,
        "retries": result.retries,
        "error_type": result.error_type,
    }
