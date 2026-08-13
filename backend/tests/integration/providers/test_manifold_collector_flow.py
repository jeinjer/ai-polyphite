from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.markets.services import ServiceDependencies
from predictionlab.collectors import CollectorConfig, MarketDataCollector
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.collector_state import (
    PostgresProviderCollectionLock,
    SqlAlchemyCollectorCheckpointStore,
)
from predictionlab.infrastructure.database.models import (
    CollectorCheckpointModel,
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    ProviderModel,
)
from predictionlab.infrastructure.database.unit_of_work import (
    SqlAlchemyMarketUnitOfWork,
)
from predictionlab.providers.manifold import ManifoldProvider

FIXTURES = Path(__file__).parents[2] / "fixtures" / "manifold"
COLLECTOR_CLOCK = datetime(2026, 7, 28, 12, tzinfo=UTC)


class FixtureManifoldProvider(ManifoldProvider):
    def __init__(
        self,
        *,
        code: str,
        http_client: httpx.AsyncClient,
        sync_mode: Literal["catalog", "recent"] = "catalog",
    ) -> None:
        super().__init__(
            http_client=http_client,
            clock=lambda: COLLECTOR_CLOCK,
            sleep=_no_sleep,
            sync_mode=sync_mode,
        )
        self._fixture_code = code

    @property
    def code(self) -> str:
        return self._fixture_code


async def _no_sleep(_: float) -> None:
    return None


def _fixture_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v0/search-markets":
        before_time = request.url.params.get("beforeTime")
        if before_time is None:
            content = (FIXTURES / "markets_page_1.json").read_bytes()
        elif before_time == "1710000001000":
            content = (FIXTURES / "markets_page_2.json").read_bytes()
        else:
            content = b"[]"
        return httpx.Response(200, content=content, request=request)

    market_id = request.url.path.removeprefix("/v0/market/")
    fixture = FIXTURES / f"market_{market_id}.json"
    if not fixture.exists():
        return httpx.Response(404, request=request)
    return httpx.Response(200, content=fixture.read_bytes(), request=request)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manifold_fixture_flows_through_collector_postgres_and_api() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_code = f"manifold_{uuid4().hex[:12]}"

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_fixture_response)
    ) as provider_client:
        provider = FixtureManifoldProvider(
            code=provider_code,
            http_client=provider_client,
        )
        collector = MarketDataCollector(
            provider=provider,
            application_dependencies=ServiceDependencies(
                unit_of_work=unit_of_work,
                clock=lambda: COLLECTOR_CLOCK,
                id_factory=uuid4,
            ),
            checkpoint_store=SqlAlchemyCollectorCheckpointStore(session_factory),
            collection_lock=PostgresProviderCollectionLock(engine),
            config=CollectorConfig(page_size=3),
            clock=lambda: COLLECTOR_CLOCK,
            sleep=_no_sleep,
        )

        try:
            result = await collector.collect(correlation_id="manifold-fixture-integration")

            assert result.pages == 3
            assert result.markets_fetched == 4
            assert result.markets_created == 4
            assert result.snapshots_fetched == 0
            assert result.snapshots_skipped == 0
            assert result.snapshots_created == 0
            assert result.observations_created == 4

            async with session_factory() as session:
                provider_id = await session.scalar(
                    select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
                )
                assert provider_id is not None
                markets = (
                    await session.scalars(
                        select(MarketModel)
                        .where(MarketModel.provider_id == provider_id)
                        .order_by(MarketModel.provider_market_id)
                    )
                ).all()
                snapshot_count = await session.scalar(
                    select(func.count())
                    .select_from(MarketSnapshotModel)
                    .join(
                        MarketModel,
                        MarketModel.market_id == MarketSnapshotModel.market_id,
                    )
                    .where(MarketModel.provider_id == provider_id)
                )
                observations = (
                    await session.scalars(
                        select(MarketObservationModel)
                        .join(
                            MarketModel,
                            MarketModel.market_id == MarketObservationModel.market_id,
                        )
                        .where(MarketModel.provider_id == provider_id)
                    )
                ).all()

            assert len(markets) == 4
            assert {market.status for market in markets} == {
                "open",
                "closed",
                "resolved",
                "cancelled",
            }
            assert all(market.source_created_at is not None for market in markets)
            assert all(market.ingested_at == COLLECTOR_CLOCK for market in markets)
            assert snapshot_count == 0
            assert len(observations) == 4
            assert all(observation.probability is not None for observation in observations)
            assert sum(observation.liquidity is not None for observation in observations) == 1
            assert sum(observation.volume is None for observation in observations) == 1
            resolved = next(
                market for market in markets if market.provider_market_id == "binary-resolved"
            )
            cancelled = next(
                market for market in markets if market.provider_market_id == "binary-cancelled"
            )
            assert resolved.resolution_outcome == "yes"
            assert resolved.resolved_at is not None
            assert resolved.resolution_source == "manifold_public_api"
            assert cancelled.resolution_outcome == "cancelled"

            application = create_app(settings)
            async with application.router.lifespan_context(application):
                transport = httpx.ASGITransport(app=application)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as client:
                    response = await client.get(
                        "/markets",
                        params={"provider": provider_code, "page_size": 10},
                    )

            assert response.status_code == 200
            payload = response.json()
            assert payload["total"] == 4
            assert {item["provider_market_id"] for item in payload["items"]} == {
                "binary-open",
                "binary-closed",
                "binary-resolved",
                "binary-cancelled",
            }
            assert all(item["source_created_at"] for item in payload["items"])
            assert all(item["ingested_at"] for item in payload["items"])
        finally:
            await _cleanup(session_factory, provider_code)
            await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recent_resolution_sweep_updates_market_missed_by_general_feed() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_code = f"manifold_{uuid4().hex[:12]}"
    resolution_visible = [False]
    pending = json.loads(
        (FIXTURES / "market_binary-late-resolution-open.json").read_text(
            encoding="utf-8"
        )
    )
    resolved = json.loads(
        (FIXTURES / "market_binary-late-resolution-resolved.json").read_text(
            encoding="utf-8"
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        market_filter = request.url.params.get("filter")
        if market_filter == "resolved":
            payload = [resolved] if resolution_visible[0] else []
        elif market_filter == "all":
            payload = [pending]
        else:
            payload = []
        return httpx.Response(200, json=payload, request=request)

    def unit_of_work() -> SqlAlchemyMarketUnitOfWork:
        return SqlAlchemyMarketUnitOfWork(session_factory)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as provider_client:
        provider = FixtureManifoldProvider(
            code=provider_code,
            http_client=provider_client,
            sync_mode="recent",
        )
        collector = MarketDataCollector(
            provider=provider,
            application_dependencies=ServiceDependencies(
                unit_of_work=unit_of_work,
                clock=lambda: COLLECTOR_CLOCK,
                id_factory=uuid4,
            ),
            checkpoint_store=SqlAlchemyCollectorCheckpointStore(session_factory),
            collection_lock=PostgresProviderCollectionLock(engine),
            config=CollectorConfig(page_size=300, max_pages_per_run=1),
            clock=lambda: COLLECTOR_CLOCK,
            sleep=_no_sleep,
        )

        try:
            first = await collector.collect(correlation_id="late-resolution-pending")
            async with session_factory() as session:
                initial = await session.scalar(
                    select(MarketModel)
                    .join(ProviderModel)
                    .where(
                        ProviderModel.code == provider_code,
                        MarketModel.provider_market_id == "binary-late-resolution",
                    )
                )

            assert first.markets_created == 1
            assert initial is not None
            assert initial.status == "closed"
            assert initial.resolution_outcome == "unresolved"

            resolution_visible[0] = True
            second = await collector.collect(correlation_id="late-resolution-resolved")
            async with session_factory() as session:
                updated = await session.scalar(
                    select(MarketModel)
                    .join(ProviderModel)
                    .where(
                        ProviderModel.code == provider_code,
                        MarketModel.provider_market_id == "binary-late-resolution",
                    )
                )

            assert second.markets_updated == 1
            assert updated is not None
            assert updated.status == "resolved"
            assert updated.resolution_outcome == "no"
            assert updated.resolved_at is not None
            assert updated.resolution_source == "manifold_public_api"
        finally:
            await _cleanup(session_factory, provider_code)
            await engine.dispose()


async def _cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    provider_code: str,
) -> None:
    async with session_factory.begin() as session:
        provider_id = await session.scalar(
            select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
        )
        if provider_id is not None:
            market_ids = select(MarketModel.market_id).where(MarketModel.provider_id == provider_id)
            await session.execute(
                delete(MarketSnapshotModel).where(MarketSnapshotModel.market_id.in_(market_ids))
            )
            await session.execute(
                delete(MarketObservationModel).where(
                    MarketObservationModel.market_id.in_(market_ids)
                )
            )
            await session.execute(
                delete(MarketStateChangeModel).where(
                    MarketStateChangeModel.market_id.in_(market_ids)
                )
            )
            await session.execute(delete(MarketModel).where(MarketModel.provider_id == provider_id))
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await session.execute(
            delete(CollectorCheckpointModel).where(
                CollectorCheckpointModel.provider_code == provider_code
            )
        )
