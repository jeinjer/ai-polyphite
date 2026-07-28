"""Local lock implementation for tests and single-process development."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class LocalProviderCollectionLock:
    """Prevent overlapping runs inside one process."""

    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._active_providers: set[str] = set()

    @asynccontextmanager
    async def acquire(self, provider_code: str) -> AsyncIterator[bool]:
        async with self._guard:
            acquired = provider_code not in self._active_providers
            if acquired:
                self._active_providers.add(provider_code)
        try:
            yield acquired
        finally:
            if acquired:
                async with self._guard:
                    self._active_providers.remove(provider_code)
