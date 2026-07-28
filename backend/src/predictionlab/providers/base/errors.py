"""Typed errors exposed by the Provider SDK."""

from __future__ import annotations

from math import isfinite


class ProviderError(Exception):
    """Base class for provider-boundary failures."""


class TransientProviderError(ProviderError):
    """Base class for failures that may succeed when retried."""


class ProviderUnavailableError(TransientProviderError):
    """Raised when a provider cannot currently serve data."""


class ProviderRateLimitError(TransientProviderError):
    """Raised when a provider asks the consumer to retry later."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        if retry_after_seconds is not None and (
            not isfinite(retry_after_seconds) or retry_after_seconds < 0
        ):
            raise ValueError("retry_after_seconds must be finite and non-negative.")
        super().__init__(message)
        self.retry_after_seconds: float | None = retry_after_seconds


class ProviderProtocolError(ProviderError):
    """Raised when a provider response violates its documented contract."""


class ProviderAuthenticationError(ProviderError):
    """Raised when a provider unexpectedly rejects authentication."""


class ProviderMarketNotFoundError(ProviderError):
    """Raised when a requested external market does not exist."""


class ProviderCapabilityError(ProviderError):
    """Raised when a provider does not support a requested capability."""


class DuplicateProviderError(ProviderError):
    """Raised when a provider code is registered more than once."""


class UnknownProviderError(ProviderError):
    """Raised when a provider code is absent from a registry."""


class InvalidProviderFactoryError(ProviderError):
    """Raised when a provider factory violates the registry contract."""
