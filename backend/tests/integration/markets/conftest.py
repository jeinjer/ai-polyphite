from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from predictionlab.core.settings import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    settings = Settings(_env_file=None)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", str(settings.database_url))
    command.upgrade(config, "head")


@pytest_asyncio.fixture
async def db_session(
    migrated_database: None,
) -> AsyncIterator[AsyncSession]:
    del migrated_database
    settings = Settings(_env_file=None)
    engine = create_async_engine(str(settings.database_url))

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()

    await engine.dispose()
