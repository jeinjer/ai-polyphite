"""Abstract provider contract and common health-check behavior."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from time import perf_counter

from predictionlab.core.clock import SystemClock
from predictionlab.providers.base.capabilities import ProviderCapabilities
from predictionlab.providers.base.health import ProviderHealth, ProviderHealthStatus
from predictionlab.providers.base.models import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    SnapshotBatch,
)

logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    """Async, provider-neutral boundary for external market data."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or SystemClock()

    @property
    @abstractmethod
    def code(self) -> str:
        """Stable registry and persistence identifier."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Operations implemented by this provider."""

    @abstractmethod
    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        """Fetch a normalized page from the provider catalog."""

    @abstractmethod
    async def fetch_market(self, provider_market_id: str) -> ProviderMarket | None:
        """Fetch one normalized market, or ``None`` when absent."""

    @abstractmethod
    async def fetch_latest_snapshot(
        self,
        provider_market_id: str,
    ) -> ProviderMarketSnapshot | None:
        """Fetch the newest snapshot for an external market."""

    @abstractmethod
    async def fetch_latest_observation(
        self,
        provider_market_id: str,
    ) -> ProviderMarketObservation | None:
        """Fetch the newest non-executable market observation."""

    @abstractmethod
    async def fetch_snapshots(
        self,
        request: FetchSnapshotsRequest,
    ) -> SnapshotBatch:
        """Fetch a normalized page of historical snapshots."""

    @abstractmethod
    async def _probe_health(self) -> ProviderHealthStatus:
        """Return health quality, or raise when the provider is unavailable."""

    async def health_check(self) -> ProviderHealth:
        """Return a safe health result; provider exceptions never escape."""

        started_at = perf_counter()
        error_type: str | None = None
        status = ProviderHealthStatus.HEALTHY
        try:
            status = await self._probe_health()
        except Exception as exc:  # Providers may fail with third-party exceptions.
            status = ProviderHealthStatus.UNHEALTHY
            error_type = type(exc).__name__
            logger.warning(
                "provider_health_check_failed",
                extra={"provider_code": self.code, "error_type": error_type},
            )

        checked_at = self._clock()
        latency_ms = (perf_counter() - started_at) * 1000
        return ProviderHealth(
            provider_code=self.code,
            status=status,
            checked_at=checked_at,
            latency_ms=latency_ms,
            error_type=error_type,
        )
