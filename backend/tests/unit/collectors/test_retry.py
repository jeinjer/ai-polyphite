from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from predictionlab.collectors.retry import ProviderRetryExecutor, RetryPolicy
from predictionlab.providers.base import ProviderError, ProviderRateLimitError


@pytest.mark.asyncio
async def test_retry_executor_uses_backoff_jitter_and_retry_after() -> None:
    delays: list[float] = []
    attempts = 0
    retry_callbacks = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProviderRateLimitError("limited", retry_after_seconds=0.5)
        if attempts == 2:
            raise ProviderRateLimitError("limited")
        return "ok"

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    def record_retry() -> None:
        nonlocal retry_callbacks
        retry_callbacks += 1

    executor = ProviderRetryExecutor(
        RetryPolicy(
            max_attempts=3,
            base_delay_seconds=0.1,
            max_delay_seconds=1,
            jitter_ratio=0.5,
        ),
        sleep=record_sleep,
        random_source=lambda: 1,
    )

    result = await executor.execute(
        operation,
        operation_name="test",
        context={"provider_code": "mock"},
        on_retry=record_retry,
    )

    assert result.value == "ok"
    assert result.retries == 2
    assert attempts == 3
    assert retry_callbacks == 2
    assert delays == [0.5, pytest.approx(0.3)]


@pytest.mark.asyncio
async def test_retry_executor_does_not_retry_non_transient_failures() -> None:
    attempts = 0
    sleep: Callable[[float], Awaitable[None]]

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ProviderError("invalid response")

    async def unexpected_sleep(delay: float) -> None:
        del delay
        raise AssertionError("sleep should not be called")

    sleep = unexpected_sleep
    executor = ProviderRetryExecutor(
        RetryPolicy(),
        sleep=sleep,
    )

    with pytest.raises(ProviderError):
        await executor.execute(
            operation,
            operation_name="test",
            context={"provider_code": "mock"},
        )

    assert attempts == 1
