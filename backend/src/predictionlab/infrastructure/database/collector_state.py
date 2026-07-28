"""PostgreSQL checkpoint and distributed-lock adapters for collectors."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from predictionlab.collectors.models import (
    CollectorCheckpoint,
    CollectorRunResult,
    CollectorRunStarted,
)
from predictionlab.infrastructure.database.models import (
    CollectorCheckpointModel,
    CollectorRunModel,
)

_LOCK_NAMESPACE = "predictionlab:market-collector:"


class SqlAlchemyCollectorCheckpointStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, provider_code: str) -> CollectorCheckpoint | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(CollectorCheckpointModel).where(
                    CollectorCheckpointModel.provider_code == provider_code
                )
            )
        return _checkpoint(model) if model is not None else None

    async def save(self, checkpoint: CollectorCheckpoint) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                insert(CollectorCheckpointModel)
                .values(
                    provider_code=checkpoint.provider_code,
                    cursor=checkpoint.cursor,
                    watermark=checkpoint.watermark,
                    pending_watermark=checkpoint.pending_watermark,
                    updated_at=checkpoint.updated_at,
                )
                .on_conflict_do_update(
                    index_elements=[CollectorCheckpointModel.provider_code],
                    set_={
                        "cursor": checkpoint.cursor,
                        "watermark": checkpoint.watermark,
                        "pending_watermark": checkpoint.pending_watermark,
                        "updated_at": checkpoint.updated_at,
                    },
                )
            )


class SqlAlchemyCollectorRunStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def start(self, run: CollectorRunStarted) -> None:
        async with self._session_factory.begin() as session:
            session.add(
                CollectorRunModel(
                    run_id=run.run_id,
                    provider_code=run.provider_code,
                    started_at=run.started_at,
                    finished_at=None,
                    status="running",
                    markets_fetched=0,
                    markets_created=0,
                    markets_updated=0,
                    markets_unchanged=0,
                    observations_fetched=0,
                    observations_created=0,
                    observations_duplicated=0,
                    observations_skipped=0,
                    retry_count=0,
                    duration_ms=None,
                    safe_error_type=None,
                    correlation_id=run.correlation_id,
                )
            )

    async def finish(self, result: CollectorRunResult) -> None:
        async with self._session_factory.begin() as session:
            updated_id = await session.scalar(
                update(CollectorRunModel)
                .where(CollectorRunModel.run_id == result.run_id)
                .values(
                    finished_at=result.finished_at,
                    status=result.status.value,
                    markets_fetched=result.markets_fetched,
                    markets_created=result.markets_created,
                    markets_updated=result.markets_updated,
                    markets_unchanged=result.markets_unchanged,
                    observations_fetched=result.observations_fetched,
                    observations_created=result.observations_created,
                    observations_duplicated=result.observations_duplicate,
                    observations_skipped=result.observations_skipped,
                    retry_count=result.retries,
                    duration_ms=result.duration_ms,
                    safe_error_type=result.error_type,
                )
                .returning(CollectorRunModel.run_id)
            )
            if updated_id is None:
                raise RuntimeError("collector run disappeared before completion")


class PostgresProviderCollectionLock:
    """Transaction-scoped advisory lock shared by all collector processes."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def acquire(self, provider_code: str) -> AsyncIterator[bool]:
        lock_key = f"{_LOCK_NAMESPACE}{provider_code}"
        async with self._engine.connect() as connection, connection.begin():
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )
            yield acquired is True


def _checkpoint(model: CollectorCheckpointModel) -> CollectorCheckpoint:
    return CollectorCheckpoint(
        provider_code=model.provider_code,
        cursor=model.cursor,
        watermark=model.watermark,
        pending_watermark=model.pending_watermark,
        updated_at=model.updated_at,
    )
