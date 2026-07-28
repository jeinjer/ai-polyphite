from __future__ import annotations

from uuid import UUID

from predictionlab.application.experiments.models import (
    ExperimentRunDetail,
    ExperimentRunPage,
    ListExperimentRuns,
    ReplayDatasetSummary,
)
from predictionlab.application.experiments.repository import (
    ExperimentRunReadRepository,
    ReplayDatasetCatalog,
)


class ExperimentRunNotFoundError(Exception):
    pass


class ExperimentRunQueryService:
    def __init__(self, repository: ExperimentRunReadRepository) -> None:
        self._repository = repository

    async def list(self, query: ListExperimentRuns) -> ExperimentRunPage:
        return await self._repository.list(query)

    async def get(self, run_id: UUID) -> ExperimentRunDetail:
        result = await self._repository.get(run_id)
        if result is None:
            raise ExperimentRunNotFoundError(str(run_id))
        return result


class ReplayDatasetQueryService:
    def __init__(self, catalog: ReplayDatasetCatalog) -> None:
        self._catalog = catalog

    def list(self) -> tuple[ReplayDatasetSummary, ...]:
        return self._catalog.list()
