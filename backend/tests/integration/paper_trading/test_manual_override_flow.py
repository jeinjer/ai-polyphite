from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from predictionlab.api.app import create_app
from predictionlab.application.predictions import RunPrediction
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PaperLedgerEntryModel,
    PaperOrderModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperTradeModel,
    PredictionRunModel,
    ProviderModel,
    TradeDecisionModel,
)
from predictionlab.runtime.predictions import create_prediction_orchestrator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_override_is_simulated_idempotent_and_separate() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        enable_manual_paper_overrides=True,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_id = uuid4()
    market_id = uuid4()
    provider_code = f"manual_override_{uuid4().hex[:10]}"
    prediction_id = None
    portfolio_id = None
    try:
        async with session_factory.begin() as session:
            session.add(
                ProviderModel(
                    provider_id=provider_id,
                    code=provider_code,
                    name="Manual override integration",
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                MarketModel(
                    market_id=market_id,
                    provider_id=provider_id,
                    provider_market_id=f"manual-{market_id}",
                    title="Manual override market",
                    description="A binary simulated test.",
                    category="testing",
                    resolution_at=now + timedelta(days=1),
                    source_created_at=now - timedelta(days=1),
                    status="open",
                    ingested_at=now,
                    updated_at=now,
                    resolution_outcome="unresolved",
                    resolved_at=None,
                    resolution_source=None,
                )
            )
            session.add(
                MarketStateChangeModel(
                    change_id=uuid4(),
                    market_id=market_id,
                    occurred_at=now - timedelta(minutes=1),
                    previous_status=None,
                    status="open",
                    previous_resolution_outcome=None,
                    resolution_outcome="unresolved",
                    resolved_at=None,
                    resolution_source=None,
                )
            )
            for index in range(4):
                observed_at = now - timedelta(minutes=4 - index)
                session.add(
                    MarketObservationModel(
                        observation_id=uuid4(),
                        market_id=market_id,
                        observed_at=observed_at,
                        probability=Decimal("0.55"),
                        volume=Decimal("100"),
                        liquidity=Decimal("100"),
                        source_updated_at=observed_at,
                        ingested_at=observed_at,
                        provider_code=provider_code,
                        raw_payload_hash=None,
                    )
                )

        prediction = await create_prediction_orchestrator(
            session_factory=session_factory,
            settings=settings,
        ).run(
            RunPrediction(
                market_id=market_id,
                predicted_at=now,
                correlation_id="manual-override-integration",
            )
        )
        prediction_id = prediction.prediction_run_id
        application = create_app(settings)
        payload = {
            "prediction_run_id": str(prediction_id),
            "side": "no",
            "requested_stake": "0.50",
            "override_reason": "Testing an explicit contrary hypothesis.",
            "idempotency_key": f"manual-{prediction_id}",
        }
        async with application.router.lifespan_context(
            application
        ), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        ) as client:
            first = await client.post(
                "/paper-trading/manual-trades",
                json=payload,
            )
            second = await client.post(
                "/paper-trading/manual-trades",
                json=payload,
            )

        assert first.status_code == 200
        assert first.json()["status"] == "filled"
        assert first.json()["simulation_only"] is True
        assert second.json()["status"] == "duplicate"
        assert (
            first.json()["trade_decision_id"]
            == second.json()["trade_decision_id"]
        )
        portfolio_id = UUID(first.json()["portfolio_id"])
        async with session_factory() as session:
            decision = await session.scalar(
                select(TradeDecisionModel).where(
                    TradeDecisionModel.decision_id
                    == UUID(first.json()["trade_decision_id"])
                )
            )
            assert decision is not None
            assert decision.decision_source == "manual_override"
            assert decision.side == "no"
            assert decision.override_reason == payload["override_reason"]
    finally:
        async with session_factory.begin() as session:
            if portfolio_id is not None:
                portfolio_ids = select(PaperPortfolioModel.portfolio_id).where(
                    PaperPortfolioModel.portfolio_id == portfolio_id
                )
                decision_ids = select(TradeDecisionModel.decision_id).where(
                    TradeDecisionModel.portfolio_id.in_(portfolio_ids)
                )
                order_ids = select(PaperOrderModel.order_id).where(
                    PaperOrderModel.decision_id.in_(decision_ids)
                )
                trade_ids = select(PaperTradeModel.trade_id).where(
                    PaperTradeModel.order_id.in_(order_ids)
                )
                await session.execute(
                    delete(PaperLedgerEntryModel).where(
                        PaperLedgerEntryModel.portfolio_id.in_(portfolio_ids)
                    )
                )
                await session.execute(
                    delete(PaperPositionModel).where(
                        PaperPositionModel.portfolio_id.in_(portfolio_ids)
                    )
                )
                await session.execute(
                    delete(PaperTradeModel).where(
                        PaperTradeModel.trade_id.in_(trade_ids)
                    )
                )
                await session.execute(
                    delete(PaperOrderModel).where(
                        PaperOrderModel.order_id.in_(order_ids)
                    )
                )
                await session.execute(
                    delete(TradeDecisionModel).where(
                        TradeDecisionModel.decision_id.in_(decision_ids)
                    )
                )
                await session.execute(
                    delete(PaperPortfolioModel).where(
                        PaperPortfolioModel.portfolio_id.in_(portfolio_ids)
                    )
                )
            if prediction_id is not None:
                await session.execute(
                    delete(AgentPredictionModel).where(
                        AgentPredictionModel.prediction_run_id
                        == prediction_id
                    )
                )
                await session.execute(
                    delete(PredictionRunModel).where(
                        PredictionRunModel.prediction_run_id == prediction_id
                    )
                )
            await session.execute(
                delete(MarketObservationModel).where(
                    MarketObservationModel.market_id == market_id
                )
            )
            await session.execute(
                delete(MarketStateChangeModel).where(
                    MarketStateChangeModel.market_id == market_id
                )
            )
            await session.execute(
                delete(MarketModel).where(
                    MarketModel.market_id == market_id
                )
            )
            await session.execute(
                delete(ProviderModel).where(
                    ProviderModel.provider_id == provider_id
                )
            )
        await engine.dispose()
