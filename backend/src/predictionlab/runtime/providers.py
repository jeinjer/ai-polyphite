"""Explicit composition of configured market-data providers."""

from __future__ import annotations

import asyncio

from predictionlab.application.sources import SourceHealthItem
from predictionlab.core.settings import Settings
from predictionlab.providers.base import (
    MarketDataProvider,
    ProviderRegistry,
    UnknownProviderError,
)
from predictionlab.providers.manifold import ManifoldProvider
from predictionlab.providers.mock import MockProvider


def create_configured_provider_registry(settings: Settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    for code in settings.enabled_providers:
        if code == "mock":
            registry.register("mock", MockProvider)
        elif code == "manifold":
            registry.register(
                "manifold",
                lambda: ManifoldProvider(sync_mode=settings.manifold_sync_mode),
            )
        else:
            raise UnknownProviderError(
                f"Configured provider '{code}' is unknown. Supported providers: mock, manifold."
            )
    return registry


class ProviderSourceHealthRepository:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def list(self) -> tuple[SourceHealthItem, ...]:
        providers = self._registry.create_all()
        try:
            health_values = await asyncio.gather(
                *(provider.health_check() for provider in providers)
            )
            return tuple(
                SourceHealthItem(
                    code=provider.code,
                    name=provider.name,
                    status=health.status.value,
                    checked_at=health.checked_at,
                    latency_ms=health.latency_ms,
                    safe_error_type=health.error_type,
                )
                for provider, health in zip(
                    providers,
                    health_values,
                    strict=True,
                )
            )
        finally:
            await asyncio.gather(*(_close_provider(provider) for provider in providers))


async def _close_provider(provider: MarketDataProvider) -> None:
    close = getattr(provider, "aclose", None)
    if close is not None:
        await close()
