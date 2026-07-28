from __future__ import annotations

from typing import Protocol
from uuid import UUID

from predictionlab.application.experiments.models import (
    ExperimentRunDetail,
    ExperimentRunPage,
    ListExperimentRuns,
    ReplayDatasetSummary,
)
from predictionlab.domain.experiments import ExperimentRun


class ExperimentRunStore(Protocol):
    async def start(self, run: ExperimentRun) -> None: ...

    async def finish(self, run: ExperimentRun) -> None: ...


class ExperimentRunReadRepository(Protocol):
    async def list(self, query: ListExperimentRuns) -> ExperimentRunPage: ...

    async def get(self, run_id: UUID) -> ExperimentRunDetail | None: ...


class ReplayDatasetCatalog(Protocol):
    def list(self) -> tuple[ReplayDatasetSummary, ...]: ...
