from __future__ import annotations

import pytest

from predictionlab.providers.base import (
    DuplicateProviderError,
    InvalidProviderFactoryError,
    ProviderCapabilities,
    ProviderCapability,
    ProviderCapabilityError,
    ProviderRegistry,
    UnknownProviderError,
)
from predictionlab.providers.mock import MockProvider


class WrongCodeMockProvider(MockProvider):
    @property
    def code(self) -> str:
        return "wrong-code"


def test_capabilities_support_and_require_features() -> None:
    capabilities = ProviderCapabilities.of(
        ProviderCapability.MARKET_LISTING,
        ProviderCapability.MARKET_DETAIL,
    )

    assert capabilities.supports(ProviderCapability.MARKET_LISTING)
    capabilities.require(ProviderCapability.MARKET_DETAIL)

    with pytest.raises(ProviderCapabilityError, match="historical_snapshots"):
        capabilities.require(ProviderCapability.HISTORICAL_SNAPSHOTS)


def test_registry_creates_registered_providers_without_global_state() -> None:
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    first = registry.create("MOCK")
    second = registry.create("mock")

    assert isinstance(first, MockProvider)
    assert isinstance(second, MockProvider)
    assert first is not second
    assert registry.registered_codes == ("mock",)
    assert len(registry.create_all()) == 1


def test_registry_rejects_duplicates_unknown_codes_and_factory_mismatches() -> None:
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    with pytest.raises(DuplicateProviderError):
        registry.register("mock", MockProvider)
    with pytest.raises(UnknownProviderError):
        registry.create("missing")

    mismatched = ProviderRegistry()
    mismatched.register("mock", WrongCodeMockProvider)
    with pytest.raises(InvalidProviderFactoryError, match="wrong-code"):
        mismatched.create("mock")

    with pytest.raises(ValueError, match="lowercase"):
        ProviderRegistry().register("invalid code", MockProvider)
