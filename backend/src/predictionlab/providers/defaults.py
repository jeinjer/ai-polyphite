"""Default provider composition for local development and tests."""

from predictionlab.providers.base.registry import ProviderRegistry
from predictionlab.providers.mock import MockProvider


def create_default_provider_registry() -> ProviderRegistry:
    """Build a new registry containing only deterministic local providers."""

    registry = ProviderRegistry()
    registry.register("mock", MockProvider)
    return registry
