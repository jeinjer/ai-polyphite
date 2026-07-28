"""Explicit registry and factory for configured providers."""

from __future__ import annotations

import re
from collections.abc import Callable
from threading import RLock

from predictionlab.providers.base.errors import (
    DuplicateProviderError,
    InvalidProviderFactoryError,
    UnknownProviderError,
)
from predictionlab.providers.base.provider import MarketDataProvider

ProviderFactory = Callable[[], MarketDataProvider]
_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ProviderRegistry:
    """Thread-safe registry without process-global mutable state."""

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}
        self._lock = RLock()

    def register(self, code: str, factory: ProviderFactory) -> None:
        normalized_code = self._normalize_code(code)
        if not callable(factory):
            raise InvalidProviderFactoryError("Provider factory must be callable.")
        with self._lock:
            if normalized_code in self._factories:
                raise DuplicateProviderError(f"Provider '{normalized_code}' is already registered.")
            self._factories[normalized_code] = factory

    def create(self, code: str) -> MarketDataProvider:
        normalized_code = self._normalize_code(code)
        with self._lock:
            factory = self._factories.get(normalized_code)
        if factory is None:
            raise UnknownProviderError(f"Provider '{normalized_code}' is not registered.")

        provider = factory()
        if not isinstance(provider, MarketDataProvider):
            raise InvalidProviderFactoryError(
                f"Factory for '{normalized_code}' did not return a MarketDataProvider."
            )
        if provider.code != normalized_code:
            raise InvalidProviderFactoryError(
                f"Factory registered as '{normalized_code}' returned provider '{provider.code}'."
            )
        return provider

    @property
    def registered_codes(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._factories))

    def create_all(self) -> tuple[MarketDataProvider, ...]:
        return tuple(self.create(code) for code in self.registered_codes)

    @staticmethod
    def _normalize_code(code: str) -> str:
        normalized_code = code.strip().lower()
        if not _PROVIDER_CODE_PATTERN.fullmatch(normalized_code):
            raise ValueError(
                "Provider code must be lowercase and contain only letters, digits, '_' or '-'."
            )
        return normalized_code
