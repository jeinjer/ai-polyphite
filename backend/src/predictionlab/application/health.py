from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ComponentStatus(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    status: ComponentStatus
    latency_ms: float


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    checks: tuple[ComponentHealth, ...]

    @property
    def ready(self) -> bool:
        return all(check.status is ComponentStatus.UP for check in self.checks)


class ReadinessChecker(Protocol):
    async def check(self) -> ReadinessReport: ...
