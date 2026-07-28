"""Provider SDK for external prediction-market data sources."""

from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    MarketDataProvider,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderRegistry,
    ProviderResolutionOutcome,
    SnapshotBatch,
)
from predictionlab.providers.defaults import create_default_provider_registry
from predictionlab.providers.manifold import ManifoldProvider
from predictionlab.providers.mock import MockProvider
from predictionlab.providers.replay import ReplayProvider

__all__ = [
    "FetchMarketsRequest",
    "FetchSnapshotsRequest",
    "ManifoldProvider",
    "MarketBatch",
    "MarketDataProvider",
    "MockProvider",
    "ProviderCapabilities",
    "ProviderCapability",
    "ProviderHealth",
    "ProviderHealthStatus",
    "ProviderMarket",
    "ProviderMarketObservation",
    "ProviderMarketSnapshot",
    "ProviderMarketStatus",
    "ProviderRegistry",
    "ProviderResolutionOutcome",
    "ReplayProvider",
    "SnapshotBatch",
    "create_default_provider_registry",
]
