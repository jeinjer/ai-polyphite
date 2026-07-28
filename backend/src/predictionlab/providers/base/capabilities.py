"""Provider feature discovery without concrete-provider type checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from predictionlab.providers.base.errors import ProviderCapabilityError


class ProviderCapability(StrEnum):
    """Optional data operations that a provider can expose."""

    MARKET_LISTING = "market_listing"
    MARKET_DETAIL = "market_detail"
    LATEST_SNAPSHOT = "latest_snapshot"
    LATEST_OBSERVATION = "latest_observation"
    HISTORICAL_SNAPSHOTS = "historical_snapshots"
    INCREMENTAL_MARKETS = "incremental_markets"


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Immutable set of capabilities advertised by a provider."""

    values: frozenset[ProviderCapability] = frozenset()

    @classmethod
    def of(
        cls,
        *capabilities: ProviderCapability,
    ) -> ProviderCapabilities:
        return cls(values=frozenset(capabilities))

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.values

    def require(self, capability: ProviderCapability) -> None:
        if not self.supports(capability):
            raise ProviderCapabilityError(
                f"Provider does not support capability '{capability.value}'."
            )
