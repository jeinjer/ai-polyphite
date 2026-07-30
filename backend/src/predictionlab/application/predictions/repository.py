from __future__ import annotations

from datetime import datetime
from typing import Protocol, Self
from uuid import UUID

from predictionlab.application.predictions.models import (
    ListPredictions,
    MarketPredictionSnapshot,
    PredictionListPage,
    PredictionRunDetail,
    PredictionRunPage,
    ResolvedPredictionSample,
)
from predictionlab.domain.predictions import PredictionRun


class PredictionIdempotencyConflictError(Exception):
    pass


class PredictionMarketRepository(Protocol):
    async def get_as_of(
        self,
        market_id: UUID,
        predicted_at: datetime,
    ) -> MarketPredictionSnapshot | None: ...

    async def list_open_ids_as_of(
        self,
        predicted_at: datetime,
        *,
        provider_codes: tuple[str, ...] = (),
        only_with_new_observations: bool = False,
    ) -> tuple[UUID, ...]: ...


class PredictionRepository(Protocol):
    async def save_if_absent(self, run: PredictionRun) -> PredictionRun: ...


class PredictionUnitOfWork(Protocol):
    predictions: PredictionRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class PredictionReadRepository(Protocol):
    async def list(self, query: ListPredictions) -> PredictionRunPage: ...

    async def list_summary(
        self,
        query: ListPredictions,
    ) -> PredictionListPage: ...

    async def get(self, prediction_id: UUID) -> PredictionRunDetail | None: ...

    async def resolved_samples(
        self,
        *,
        experiment_run_id: UUID | None,
    ) -> tuple[ResolvedPredictionSample, ...]: ...
