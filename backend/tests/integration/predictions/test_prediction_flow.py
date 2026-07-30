from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.predictions import (
    PredictionIdempotencyConflictError,
    RunPrediction,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PredictionRunModel,
    ProviderModel,
)
from predictionlab.infrastructure.database.queries import (
    SqlAlchemyPredictionReadRepository,
)
from predictionlab.runtime.predictions import create_prediction_orchestrator

NOW = datetime(2026, 2, 1, 12, tzinfo=UTC)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prediction_pipeline_is_as_of_idempotent_persisted_and_queryable() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        enable_manual_prediction_runs=True,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_id = uuid4()
    market_id = uuid4()
    provider_code = f"prediction_{uuid4().hex[:10]}"
    observation_ids = [uuid4(), uuid4(), uuid4()]
    change_id = uuid4()
    prediction_id = None
    try:
        async with session_factory.begin() as session:
            session.add(
                ProviderModel(
                    provider_id=provider_id,
                    code=provider_code,
                    name="Prediction test provider",
                    enabled=True,
                    created_at=NOW - timedelta(days=1),
                    updated_at=NOW - timedelta(days=1),
                )
            )
            session.add(
                MarketModel(
                    market_id=market_id,
                    provider_id=provider_id,
                    provider_market_id=f"external-{market_id}",
                    title="¿Se mantendrá la barrera temporal?",
                    description="Mercado de integración.",
                    category="testing",
                    resolution_at=NOW + timedelta(days=3),
                    source_created_at=NOW - timedelta(days=1),
                    status="open",
                    resolution_outcome="unresolved",
                    resolved_at=None,
                    resolution_source=None,
                    ingested_at=NOW - timedelta(days=1),
                    updated_at=NOW,
                )
            )
            session.add(
                MarketStateChangeModel(
                    change_id=change_id,
                    market_id=market_id,
                    occurred_at=NOW - timedelta(days=1),
                    previous_status=None,
                    status="open",
                    previous_resolution_outcome=None,
                    resolution_outcome="unresolved",
                    resolved_at=None,
                    resolution_source=None,
                )
            )
            for observation_id, observed_at, probability in (
                (
                    observation_ids[0],
                    NOW - timedelta(hours=2),
                    Decimal("0.40"),
                ),
                (observation_ids[1], NOW, Decimal("0.55")),
                (
                    observation_ids[2],
                    NOW + timedelta(hours=2),
                    Decimal("0.99"),
                ),
            ):
                session.add(
                    MarketObservationModel(
                        observation_id=observation_id,
                        market_id=market_id,
                        observed_at=observed_at,
                        probability=probability,
                        volume=Decimal("100"),
                        liquidity=Decimal("50"),
                        source_updated_at=observed_at,
                        ingested_at=observed_at,
                        provider_code=provider_code,
                        raw_payload_hash=None,
                    )
                )

        orchestrator = create_prediction_orchestrator(
            session_factory=session_factory,
            settings=settings,
        )
        command = RunPrediction(
            market_id=market_id,
            predicted_at=NOW,
            context={"probability_adjustment": "0.15"},
            correlation_id="integration-prediction",
        )
        first = await orchestrator.run(command)
        second = await orchestrator.run(command)
        prediction_id = first.prediction_run_id

        assert first.prediction_run_id == second.prediction_run_id
        assert first.market_probability == Decimal("0.55")
        assert len(first.agent_predictions) == 4
        with pytest.raises(PredictionIdempotencyConflictError):
            await orchestrator.run(
                RunPrediction(
                    market_id=market_id,
                    predicted_at=NOW,
                    context={"probability_adjustment": "-0.15"},
                    correlation_id="integration-conflict",
                )
            )

        repository = SqlAlchemyPredictionReadRepository(session_factory)
        detail = await repository.get(first.prediction_run_id)
        assert detail is not None
        assert len(detail.agent_predictions) == 4

        application = create_app(settings)
        async with (
            application.router.lifespan_context(application),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application),
                base_url="http://testserver",
            ) as client,
        ):
            listing = await client.get(
                f"/markets/{market_id}/predictions",
                params={"page_size": 10},
            )
            response = await client.get(f"/predictions/{first.prediction_run_id}")
            summaries = await client.get(
                "/predictions",
                params={
                    "provider": provider_code,
                    "page_size": 25,
                    "sort": "consensus_probability",
                    "direction": "desc",
                },
            )

        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert response.status_code == 200
        assert response.json()["market_probability"] == "0.5500000000"
        assert len(response.json()["agent_predictions"]) == 4
        assert summaries.status_code == 200
        assert summaries.json()["total_items"] == 1
        assert summaries.json()["items"][0]["commercial_label"] == "not_evaluable"
        assert "agent_predictions" not in summaries.json()["items"][0]
    finally:
        async with session_factory.begin() as session:
            if prediction_id is not None:
                await session.execute(
                    delete(AgentPredictionModel).where(
                        AgentPredictionModel.prediction_run_id == prediction_id
                    )
                )
                await session.execute(
                    delete(PredictionRunModel).where(
                        PredictionRunModel.prediction_run_id == prediction_id
                    )
                )
            await session.execute(
                delete(MarketObservationModel).where(MarketObservationModel.market_id == market_id)
            )
            await session.execute(
                delete(MarketStateChangeModel).where(MarketStateChangeModel.market_id == market_id)
            )
            await session.execute(delete(MarketModel).where(MarketModel.market_id == market_id))
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await engine.dispose()
