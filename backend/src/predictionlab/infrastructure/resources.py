from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from predictionlab.core.settings import Settings
from predictionlab.infrastructure.health.readiness import (
    DependencyCheck,
    ReadinessService,
)


@dataclass(frozen=True, slots=True)
class InfrastructureResources:
    database_engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis_client: Redis
    readiness: ReadinessService

    async def close(self) -> None:
        await asyncio.gather(
            self.redis_client.aclose(),
            self.database_engine.dispose(),
        )


def create_resources(settings: Settings) -> InfrastructureResources:
    database_engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )
    redis_client = Redis.from_url(
        str(settings.redis_url),
        decode_responses=True,
    )
    session_factory = async_sessionmaker(
        database_engine,
        expire_on_commit=False,
    )
    readiness = ReadinessService(
        checks=(
            DependencyCheck(
                name="postgres",
                run=partial(_check_postgres, database_engine),
            ),
            DependencyCheck(
                name="redis",
                run=partial(_check_redis, redis_client),
            ),
        ),
        timeout_seconds=settings.readiness_timeout_seconds,
    )
    return InfrastructureResources(
        database_engine=database_engine,
        session_factory=session_factory,
        redis_client=redis_client,
        readiness=readiness,
    )


async def _check_postgres(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_redis(client: Redis) -> None:
    response = await client.ping()
    if response is not True:
        raise RuntimeError("Redis ping returned an unexpected response")
