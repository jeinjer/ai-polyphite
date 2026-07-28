"""Collector-layer failures."""

from __future__ import annotations

from predictionlab.collectors.models import CollectorRunResult


class CollectorError(Exception):
    """Base class for collector orchestration failures."""


class CollectorProtocolError(CollectorError):
    """Raised when a provider violates cursor or DTO expectations."""


class CollectorRunFailedError(CollectorError):
    """Expose the failed run summary without leaking provider payloads."""

    def __init__(
        self,
        result: CollectorRunResult,
        *,
        retryable: bool,
    ) -> None:
        super().__init__(f"Collector run {result.run_id} failed with {result.error_type}.")
        self.result = result
        self.retryable = retryable
