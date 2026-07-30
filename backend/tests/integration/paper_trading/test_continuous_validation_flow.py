from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from predictionlab.application.paper_validation import PaperValidationRunStatus
from predictionlab.application.predictions import ListPredictions
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    CommercialEvaluationModel,
    MarketModel,
    MarketObservationModel,
    MarketStateChangeModel,
    PaperLedgerEntryModel,
    PaperOrderModel,
    PaperPerformanceSnapshotModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperSettlementModel,
    PaperTradeModel,
    PaperValidationRunModel,
    PredictionRunModel,
    ProviderModel,
    TradeDecisionModel,
)
from predictionlab.infrastructure.database.paper_validation import (
    SqlAlchemyPaperValidationRunStore,
)
from predictionlab.infrastructure.database.queries.predictions import (
    SqlAlchemyPredictionReadRepository,
)
from predictionlab.runtime.paper_validation_runtime import (
    create_paper_validation_runtime,
)

NOW = datetime(2000, 1, 2, 12, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW

    def __call__(self) -> datetime:
        return self.now()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_continuous_validation_is_idempotent_audited_and_reconciled() -> None:
    provider_code = f"paper_validation_{uuid4().hex[:10]}"
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        paper_validation_portfolio_name=f"integration-{uuid4().hex}",
        paper_validation_interval_seconds=3600,
        paper_validation_provider_codes=(provider_code,),
        paper_validation_only_new_observations=True,
        experimental_campaign_enabled=False,
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_id = uuid4()
    market_id = uuid4()
    portfolio_id: UUID | None = None
    try:
        await _seed_market(
            session_factory,
            provider_id=provider_id,
            provider_code=provider_code,
            market_id=market_id,
        )
        runtime = create_paper_validation_runtime(settings, clock=FixedClock())
        try:
            first = await runtime.worker.run_once(scheduled_for=NOW)
            second = await runtime.worker.run_once(scheduled_for=NOW)
            unchanged_cycle = await runtime.worker.run_once(scheduled_for=NOW + timedelta(hours=1))
            await _seed_observation(
                session_factory,
                provider_code=provider_code,
                market_id=market_id,
                observed_at=NOW + timedelta(hours=1, minutes=30),
            )
            next_cycle = await runtime.worker.run_once(scheduled_for=NOW + timedelta(hours=2))
            portfolio_id = first.portfolio_id
        finally:
            await runtime.close()

        assert first.status is PaperValidationRunStatus.COMPLETED
        assert first.portfolio_id is not None
        assert first.prediction_count == 1
        assert first.decision_count == 1
        assert first.reconciliation is not None
        assert first.reconciliation.is_consistent
        assert second.status is PaperValidationRunStatus.SKIPPED_COMPLETED
        assert second.portfolio_id == first.portfolio_id
        assert next_cycle.status is PaperValidationRunStatus.COMPLETED
        assert next_cycle.portfolio_id == first.portfolio_id
        assert next_cycle.cycle_key != first.cycle_key
        assert unchanged_cycle.prediction_count == 0
        assert next_cycle.prediction_count == 1

        run_store = SqlAlchemyPaperValidationRunStore(session_factory)
        reconciliation = await run_store.reconcile(
            first.portfolio_id,
            checked_at=NOW,
        )
        assert reconciliation.is_consistent
        assert reconciliation.discrepancy_codes == ()

        async with session_factory.begin() as session:
            await session.execute(
                update(PaperLedgerEntryModel)
                .where(
                    PaperLedgerEntryModel.portfolio_id == first.portfolio_id,
                    PaperLedgerEntryModel.entry_type == "initial_capital",
                )
                .values(amount=PaperLedgerEntryModel.amount - Decimal("1"))
            )
        drift = await run_store.reconcile(first.portfolio_id, checked_at=NOW)
        assert not drift.is_consistent
        assert "ledger_cash_balance" in drift.discrepancy_codes

        async with session_factory() as session:
            validation_count = await session.scalar(
                select(func.count())
                .select_from(PaperValidationRunModel)
                .where(
                    PaperValidationRunModel.portfolio_id == first.portfolio_id,
                )
            )
            prediction_count = await session.scalar(
                select(func.count())
                .select_from(PredictionRunModel)
                .where(PredictionRunModel.market_id == market_id)
            )
            decision_count = await session.scalar(
                select(func.count())
                .select_from(TradeDecisionModel)
                .where(TradeDecisionModel.portfolio_id == first.portfolio_id)
            )

        assert validation_count == 4
        assert prediction_count == 2
        assert decision_count == 2
    finally:
        await _cleanup(
            session_factory,
            provider_id=provider_id,
            market_id=market_id,
            portfolio_ids=(portfolio_id,) if portfolio_id is not None else (),
        )
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_experimental_campaign_reuses_predictions_in_a_separate_portfolio() -> None:
    provider_code = f"paper_validation_{uuid4().hex[:10]}"
    primary_name = f"conservative-{uuid4().hex}"
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        paper_validation_portfolio_name=primary_name,
        paper_validation_interval_seconds=3600,
        paper_validation_provider_codes=(provider_code,),
        paper_validation_only_new_observations=True,
        experimental_campaign_enabled=True,
        experimental_min_net_edge=Decimal("0.015"),
    )
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider_id = uuid4()
    market_id = uuid4()
    portfolio_ids: tuple[UUID, ...] = ()
    try:
        await _seed_market(
            session_factory,
            provider_id=provider_id,
            provider_code=provider_code,
            market_id=market_id,
        )
        runtime = create_paper_validation_runtime(settings, clock=FixedClock())
        try:
            result = await runtime.worker.run_once(scheduled_for=NOW)
        finally:
            await runtime.close()

        assert result.status is PaperValidationRunStatus.COMPLETED
        async with session_factory() as session:
            portfolio_rows = (
                await session.execute(
                    select(PaperPortfolioModel.portfolio_id, PaperPortfolioModel.name)
                    .join(
                        CommercialEvaluationModel,
                        CommercialEvaluationModel.portfolio_id == PaperPortfolioModel.portfolio_id,
                    )
                    .join(
                        PredictionRunModel,
                        PredictionRunModel.prediction_run_id
                        == CommercialEvaluationModel.prediction_run_id,
                    )
                    .where(PredictionRunModel.market_id == market_id)
                    .distinct()
                )
            ).all()
            campaigns = set(
                (
                    await session.scalars(
                        select(CommercialEvaluationModel.campaign_id)
                        .join(
                            PredictionRunModel,
                            PredictionRunModel.prediction_run_id
                            == CommercialEvaluationModel.prediction_run_id,
                        )
                        .where(PredictionRunModel.market_id == market_id)
                    )
                ).all()
            )
            prediction_count = await session.scalar(
                select(func.count())
                .select_from(PredictionRunModel)
                .where(PredictionRunModel.market_id == market_id)
            )
            validation_count = await session.scalar(
                select(func.count())
                .select_from(PaperValidationRunModel)
                .join(
                    PaperPortfolioModel,
                    PaperPortfolioModel.portfolio_id == PaperValidationRunModel.portfolio_id,
                )
                .where(
                    PaperPortfolioModel.portfolio_id.in_(
                        tuple(row.portfolio_id for row in portfolio_rows)
                    )
                )
            )

        portfolio_ids = tuple(row.portfolio_id for row in portfolio_rows)
        portfolio_names = {row.name for row in portfolio_rows}
        assert len(portfolio_ids) == 2
        assert any(name.startswith(primary_name) for name in portfolio_names)
        assert any(name.startswith("Experimental paper validation") for name in portfolio_names)
        assert campaigns == {"conservative-v1", "experimental-v1"}
        assert prediction_count == 1
        assert validation_count == 2
        prediction_page = await SqlAlchemyPredictionReadRepository(session_factory).list_summary(
            ListPredictions(market_id=market_id)
        )
        current = next(item for item in prediction_page.items if item.market_id == market_id)
        assert current.campaign_id == "conservative-v1"
    finally:
        await _cleanup(
            session_factory,
            provider_id=provider_id,
            market_id=market_id,
            portfolio_ids=portfolio_ids,
        )
        await engine.dispose()


async def _seed_market(
    session_factory,
    *,
    provider_id: UUID,
    provider_code: str,
    market_id: UUID,
) -> None:
    async with session_factory.begin() as session:
        session.add(
            ProviderModel(
                provider_id=provider_id,
                code=provider_code,
                name="Continuous validation integration provider",
                enabled=True,
                created_at=NOW - timedelta(days=1),
                updated_at=NOW,
            )
        )
        session.add(
            MarketModel(
                market_id=market_id,
                provider_id=provider_id,
                provider_market_id=f"external-{market_id}",
                title="Will the continuous validation cycle remain reproducible?",
                description="Isolated integration fixture.",
                category="testing",
                resolution_at=NOW + timedelta(days=30),
                source_created_at=NOW - timedelta(days=1),
                status="open",
                resolution_outcome="unresolved",
                resolved_at=None,
                resolution_source=None,
                ingested_at=NOW - timedelta(hours=1),
                updated_at=NOW,
            )
        )
        session.add(
            MarketStateChangeModel(
                change_id=uuid4(),
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
        session.add(
            MarketObservationModel(
                observation_id=uuid4(),
                market_id=market_id,
                observed_at=NOW,
                probability=Decimal("0.35"),
                volume=Decimal("100"),
                liquidity=Decimal("50"),
                source_updated_at=NOW,
                ingested_at=NOW,
                provider_code=provider_code,
                raw_payload_hash=None,
            )
        )


async def _seed_observation(
    session_factory,
    *,
    provider_code: str,
    market_id: UUID,
    observed_at: datetime,
) -> None:
    async with session_factory.begin() as session:
        session.add(
            MarketObservationModel(
                observation_id=uuid4(),
                market_id=market_id,
                observed_at=observed_at,
                probability=Decimal("0.40"),
                volume=Decimal("120"),
                liquidity=Decimal("55"),
                source_updated_at=observed_at,
                ingested_at=observed_at,
                provider_code=provider_code,
                raw_payload_hash=None,
            )
        )


async def _cleanup(
    session_factory,
    *,
    provider_id: UUID,
    market_id: UUID,
    portfolio_ids: tuple[UUID, ...],
) -> None:
    async with session_factory.begin() as session:
        for portfolio_id in portfolio_ids:
            decision_ids = select(TradeDecisionModel.decision_id).where(
                TradeDecisionModel.portfolio_id == portfolio_id
            )
            order_ids = select(PaperOrderModel.order_id).where(
                PaperOrderModel.decision_id.in_(decision_ids)
            )
            trade_ids = select(PaperTradeModel.trade_id).where(
                PaperTradeModel.order_id.in_(order_ids)
            )
            position_ids = select(PaperPositionModel.position_id).where(
                PaperPositionModel.trade_id.in_(trade_ids)
            )
            await session.execute(
                delete(PaperValidationRunModel).where(
                    PaperValidationRunModel.portfolio_id == portfolio_id
                )
            )
            await session.execute(
                delete(PaperPerformanceSnapshotModel).where(
                    PaperPerformanceSnapshotModel.portfolio_id == portfolio_id
                )
            )
            await session.execute(
                delete(PaperLedgerEntryModel).where(
                    PaperLedgerEntryModel.portfolio_id == portfolio_id
                )
            )
            await session.execute(
                delete(PaperSettlementModel).where(
                    PaperSettlementModel.position_id.in_(position_ids)
                )
            )
            await session.execute(
                delete(PaperPositionModel).where(PaperPositionModel.position_id.in_(position_ids))
            )
            await session.execute(
                delete(PaperTradeModel).where(PaperTradeModel.trade_id.in_(trade_ids))
            )
            await session.execute(
                delete(PaperOrderModel).where(PaperOrderModel.order_id.in_(order_ids))
            )
            await session.execute(
                delete(CommercialEvaluationModel).where(
                    CommercialEvaluationModel.portfolio_id == portfolio_id
                )
            )
            await session.execute(
                delete(TradeDecisionModel).where(TradeDecisionModel.decision_id.in_(decision_ids))
            )
            await session.execute(
                delete(PaperPortfolioModel).where(PaperPortfolioModel.portfolio_id == portfolio_id)
            )

        prediction_ids = select(PredictionRunModel.prediction_run_id).where(
            PredictionRunModel.market_id == market_id
        )
        await session.execute(
            delete(AgentPredictionModel).where(
                AgentPredictionModel.prediction_run_id.in_(prediction_ids)
            )
        )
        await session.execute(
            delete(PredictionRunModel).where(PredictionRunModel.market_id == market_id)
        )
        await session.execute(
            delete(MarketObservationModel).where(MarketObservationModel.market_id == market_id)
        )
        await session.execute(
            delete(MarketStateChangeModel).where(MarketStateChangeModel.market_id == market_id)
        )
        await session.execute(delete(MarketModel).where(MarketModel.market_id == market_id))
        await session.execute(delete(ProviderModel).where(ProviderModel.provider_id == provider_id))
