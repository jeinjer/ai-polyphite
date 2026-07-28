from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SourceHealthItem:
    code: str
    name: str
    status: str
    checked_at: datetime
    latency_ms: float
    safe_error_type: str | None


class SourceHealthReadRepository(Protocol):
    async def list(self) -> tuple[SourceHealthItem, ...]: ...


class SourceHealthQueryService:
    def __init__(self, repository: SourceHealthReadRepository) -> None:
        self._repository = repository

    async def list(self) -> tuple[SourceHealthItem, ...]:
        return await self._repository.list()
