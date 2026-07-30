from __future__ import annotations

from uuid import UUID

from predictionlab.application.predictions.models import (
    ListPredictions,
    PredictionListPage,
    PredictionRunDetail,
    PredictionRunPage,
)
from predictionlab.application.predictions.repository import PredictionReadRepository


class PredictionNotFoundError(Exception):
    pass


class PredictionQueryService:
    def __init__(self, repository: PredictionReadRepository) -> None:
        self._repository = repository

    async def list(self, query: ListPredictions) -> PredictionRunPage:
        return await self._repository.list(query)

    async def list_summary(
        self,
        query: ListPredictions,
    ) -> PredictionListPage:
        return await self._repository.list_summary(query)

    async def get(self, prediction_id: UUID) -> PredictionRunDetail:
        result = await self._repository.get(prediction_id)
        if result is None:
            raise PredictionNotFoundError(str(prediction_id))
        return result
