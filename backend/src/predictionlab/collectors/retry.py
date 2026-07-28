"""Selective exponential retry policy for provider operations."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from math import isfinite

from predictionlab.providers.base import (
    ProviderRateLimitError,
    TransientProviderError,
)

logger = logging.getLogger(__name__)

type AsyncSleep = Callable[[float], Awaitable[None]]
type RandomSource = Callable[[], float]
type RetryCallback = Callable[[], None]


@dataclass(frozen=True, slots=True, kw_only=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 5.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive.")
        if not isfinite(self.base_delay_seconds) or self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be finite and non-negative.")
        if not isfinite(self.max_delay_seconds) or self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds cannot be lower than base delay.")
        if not isfinite(self.jitter_ratio) or not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class RetryOutcome[T]:
    value: T
    retries: int


class ProviderRetryExecutor:
    def __init__(
        self,
        policy: RetryPolicy,
        *,
        sleep: AsyncSleep = asyncio.sleep,
        random_source: RandomSource = random.random,
    ) -> None:
        self._policy = policy
        self._sleep = sleep
        self._random_source = random_source

    async def execute[T](
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        operation_name: str,
        context: Mapping[str, object],
        on_retry: RetryCallback | None = None,
    ) -> RetryOutcome[T]:
        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                return RetryOutcome(
                    value=await operation(),
                    retries=attempt - 1,
                )
            except TransientProviderError as exc:
                if attempt >= self._policy.max_attempts:
                    raise
                delay = self._delay(attempt, exc)
                logger.warning(
                    "provider_operation_retry",
                    extra={
                        **context,
                        "operation": operation_name,
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "delay_seconds": delay,
                        "error_type": type(exc).__name__,
                    },
                )
                if on_retry is not None:
                    on_retry()
                await self._sleep(delay)

        raise RuntimeError("retry loop exited unexpectedly")

    def _delay(
        self,
        attempt: int,
        error: TransientProviderError,
    ) -> float:
        exponential = min(
            self._policy.max_delay_seconds,
            self._policy.base_delay_seconds * (2 ** (attempt - 1)),
        )
        random_value = self._random_source()
        if not 0 <= random_value <= 1:
            raise ValueError("random_source must return a value between 0 and 1.")
        delay = min(
            self._policy.max_delay_seconds,
            exponential * (1 + self._policy.jitter_ratio * random_value),
        )
        if isinstance(error, ProviderRateLimitError) and error.retry_after_seconds is not None:
            delay = max(delay, error.retry_after_seconds)
        return float(delay)
