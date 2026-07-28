"""Infrastructure ports required by the collector runtime."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from predictionlab.collectors.models import (
    CollectorCheckpoint,
    CollectorRunResult,
    CollectorRunStarted,
)


class CollectorCheckpointStore(Protocol):
    async def get(self, provider_code: str) -> CollectorCheckpoint | None: ...

    async def save(self, checkpoint: CollectorCheckpoint) -> None: ...


class ProviderCollectionLock(Protocol):
    def acquire(
        self,
        provider_code: str,
    ) -> AbstractAsyncContextManager[bool]: ...


class CollectorRunStore(Protocol):
    async def start(self, run: CollectorRunStarted) -> None: ...

    async def finish(self, result: CollectorRunResult) -> None: ...


class NullCollectorRunStore:
    async def start(self, run: CollectorRunStarted) -> None:
        del run

    async def finish(self, result: CollectorRunResult) -> None:
        del result
