from __future__ import annotations

from typing import Protocol
from uuid import UUID

from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)


class CollectorRunReadRepository(Protocol):
    async def list(self, query: ListCollectorRuns) -> CollectorRunPage: ...

    async def get(self, run_id: UUID) -> CollectorRunDetail | None: ...
