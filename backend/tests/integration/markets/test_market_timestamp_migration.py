from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from predictionlab.core.settings import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "20260728_0003_split_market_timestamps.py"
EXISTING_TIMESTAMP = datetime(2026, 7, 27, 9, 30, tzinfo=UTC)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timestamp_migration_preserves_existing_market_creation_value() -> None:
    settings = Settings(_env_file=None)
    engine = create_async_engine(str(settings.database_url))
    schema = f"migration_test_{uuid4().hex}"

    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.execute(
                text(
                    "CREATE TABLE markets ("
                    "market_id integer PRIMARY KEY, "
                    "created_at timestamp with time zone NOT NULL"
                    ")"
                )
            )
            await connection.execute(
                text("INSERT INTO markets (market_id, created_at) VALUES (1, :created_at)"),
                {"created_at": EXISTING_TIMESTAMP},
            )

            await connection.run_sync(_run_upgrade)

            columns = await connection.run_sync(
                lambda sync_connection: {
                    item["name"]: item
                    for item in inspect(sync_connection).get_columns(
                        "markets",
                        schema=schema,
                    )
                }
            )
            row = (
                await connection.execute(
                    text("SELECT ingested_at, source_created_at FROM markets WHERE market_id = 1")
                )
            ).one()

        assert "created_at" not in columns
        assert columns["ingested_at"]["nullable"] is False
        assert columns["source_created_at"]["nullable"] is True
        assert row.ingested_at == EXISTING_TIMESTAMP
        assert row.source_created_at is None
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


def _run_upgrade(connection: Connection) -> None:
    migration = _load_migration()
    original_operations = migration.op
    migration.op = Operations(MigrationContext.configure(connection))
    try:
        migration.upgrade()
    finally:
        migration.op = original_operations


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "market_timestamp_migration",
        MIGRATION_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market timestamp migration.")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration
