"""Public building blocks for market-data providers."""

from predictionlab.providers.base.capabilities import (
    ProviderCapabilities,
    ProviderCapability,
)
from predictionlab.providers.base.errors import (
    DuplicateProviderError,
    InvalidProviderFactoryError,
    ProviderAuthenticationError,
    ProviderCapabilityError,
    ProviderError,
    ProviderMarketNotFoundError,
    ProviderProtocolError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    TransientProviderError,
    UnknownProviderError,
)
from predictionlab.providers.base.health import ProviderHealth, ProviderHealthStatus
from predictionlab.providers.base.models import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderResolutionOutcome,
    SnapshotBatch,
)
from predictionlab.providers.base.provider import MarketDataProvider
from predictionlab.providers.base.registry import ProviderFactory, ProviderRegistry

__all__ = [
    "DuplicateProviderError",
    "FetchMarketsRequest",
    "FetchSnapshotsRequest",
    "InvalidProviderFactoryError",
    "MarketBatch",
    "MarketDataProvider",
    "ProviderAuthenticationError",
    "ProviderCapabilities",
    "ProviderCapability",
    "ProviderCapabilityError",
    "ProviderError",
    "ProviderFactory",
    "ProviderHealth",
    "ProviderHealthStatus",
    "ProviderMarket",
    "ProviderMarketNotFoundError",
    "ProviderMarketObservation",
    "ProviderMarketSnapshot",
    "ProviderMarketStatus",
    "ProviderProtocolError",
    "ProviderRateLimitError",
    "ProviderRegistry",
    "ProviderResolutionOutcome",
    "ProviderUnavailableError",
    "SnapshotBatch",
    "TransientProviderError",
    "UnknownProviderError",
]
