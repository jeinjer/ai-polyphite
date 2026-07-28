from __future__ import annotations

import importlib.util
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
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260728_0004_add_market_observations_and_resolution.py"
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolution_migration_preserves_and_maps_existing_markets() -> None:
    engine = create_async_engine(str(Settings(_env_file=None).database_url))
    schema = f"migration_test_{uuid4().hex}"
    open_id, resolved_id, cancelled_id = uuid4(), uuid4(), uuid4()

    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.execute(text("CREATE TABLE providers (code varchar(64) PRIMARY KEY)"))
            await connection.execute(
                text(
                    "CREATE TABLE markets (market_id uuid PRIMARY KEY, status varchar(32) NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO markets (market_id, status) VALUES "
                    "(:open_id, 'open'), "
                    "(:resolved_id, 'resolved'), "
                    "(:cancelled_id, 'cancelled')"
                ),
                {
                    "open_id": open_id,
                    "resolved_id": resolved_id,
                    "cancelled_id": cancelled_id,
                },
            )

            await connection.run_sync(_run_upgrade)

            tables = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names(schema=schema))
            )
            rows = (
                await connection.execute(
                    text("SELECT status, resolution_outcome FROM markets ORDER BY status")
                )
            ).all()

        assert {"market_observations", "market_state_history"} <= tables
        assert rows == [
            ("cancelled", "cancelled"),
            ("open", "unresolved"),
            ("resolved", "other"),
        ]
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
        "observation_resolution_migration",
        MIGRATION_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load observation/resolution migration.")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration
