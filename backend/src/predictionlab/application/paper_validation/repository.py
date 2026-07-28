"""Persistence and locking ports for paper validation."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from predictionlab.application.paper_validation.models import (
    CompletedPaperValidationCycle,
    PaperValidationRunResult,
    PaperValidationRunStarted,
    PortfolioReconciliation,
)


class PaperValidationRunStore(Protocol):
    async def start(self, run: PaperValidationRunStarted) -> None: ...

    async def finish(self, result: PaperValidationRunResult) -> None: ...

    async def find_completed(
        self,
        cycle_key: str,
    ) -> CompletedPaperValidationCycle | None: ...

    async def reconcile(
        self,
        portfolio_id: UUID,
        *,
        checked_at: datetime,
    ) -> PortfolioReconciliation: ...


class PaperValidationLock(Protocol):
    def acquire(self) -> AbstractAsyncContextManager[bool]: ...
