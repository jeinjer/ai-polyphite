from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from predictionlab.application.paper_trading import (
    ListPaperTrades,
    PaperPerformanceService,
    PaperTradingQueryService,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.paper_trading import CurrencyUnit
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    CollectorCheckpointModel,
    CollectorRunModel,
    CommercialEvaluationModel,
    ExperimentRunModel,
    MarketModel,
    MarketObservationModel,
    MarketSnapshotModel,
    MarketStateChangeModel,
    PaperLedgerEntryModel,
    PaperOrderModel,
    PaperPerformanceSnapshotModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperSettlementModel,
    PaperTradeModel,
    PredictionRunModel,
    ProviderModel,
    TradeDecisionModel,
)
from predictionlab.infrastructure.database.queries import (
    SqlAlchemyPaperTradingReadRepository,
)
from predictionlab.runtime.paper_trading_replay import PaperTradingReplayHook
from predictionlab.runtime.prediction_replay import (
    PredictionReplayHook,
    ReplayPredictionSchedule,
)
from predictionlab.runtime.replay_runner import ReplayMode
from predictionlab.runtime.replay_runtime import create_replay_runtime

DATASET = Path(__file__).parents[3] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_replay_trade_is_deterministic_persistent_and_queryable() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.CRITICAL,
        replay_dataset_directory=DATASET.parent,
    )
    provider_code = f"trade_replay_{uuid4().hex[:10]}"
    experiment_ids: list[UUID] = []
    portfolio_ids: list[UUID] = []
    paper_hashes: list[str | None] = []
    equities = []
    trade_counts: list[int] = []

    for _ in range(2):
        runtime = create_replay_runtime(
            settings,
            DATASET,
            provider_code=provider_code,
        )
        schedule = ReplayPredictionSchedule(
            replay_start=runtime.provider.metadata.replay_start,
            replay_end=runtime.provider.metadata.replay_end,
            interval=timedelta(days=5),
        )
        prediction_hook = PredictionReplayHook(
            orchestrator=runtime.prediction_orchestrator,
            schedule=schedule,
            random_seed=7,
        )
        hook = PaperTradingReplayHook(
            prediction_hook=prediction_hook,
            orchestrator=runtime.paper_trading_orchestrator,
            dataset_id="synthetic-lab-v1",
            currency_unit=CurrencyUnit.USD_SIMULATED,
            initial_balance=settings.paper_initial_balance,
        )
        try:
            execution = await runtime.runner.run(
                mode=ReplayMode.ACCELERATED,
                random_seed=7,
                artifact_hook=hook,
                extension_configuration={
                    "paper_trading": {
                        "configuration_hash": hook.configuration_hash,
                        "currency_unit": CurrencyUnit.USD_SIMULATED.value,
                    }
                },
            )
            assert hook.portfolio_id is not None
            experiment_ids.append(execution.experiment.experiment_run_id)
            portfolio_ids.append(hook.portfolio_id)
            paper_hashes.append(hook.final_result_hash)
            equities.append(hook.final_equity)
            trade_counts.append(hook.trade_count)
        finally:
            await runtime.close()

    assert paper_hashes[0] == paper_hashes[1]
    assert equities[0] == equities[1]
    assert trade_counts[0] == trade_counts[1]
    assert trade_counts[0] > 0

    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        repository = SqlAlchemyPaperTradingReadRepository(session_factory)
        query_service = PaperTradingQueryService(repository)
        performance_service = PaperPerformanceService(repository)

        trades = await query_service.list_trades(
            ListPaperTrades(portfolio_id=portfolio_ids[0], page_size=100)
        )
        report = await performance_service.evaluate(portfolio_ids[0])
        async with session_factory() as session:
            settlement_count = await session.scalar(
                select(func.count())
                .select_from(PaperSettlementModel)
                .join(PaperPositionModel)
                .where(PaperPositionModel.portfolio_id == portfolio_ids[0])
            )

        assert trades.total == trade_counts[0]
        assert trades.items[0].prediction_result_hash
        assert report.metrics.closed_trade_count == settlement_count
        assert report.metrics.net_profit == report.portfolio.equity - Decimal("100")
        assert {item.name for item in report.baselines} == {
            "no_trade",
            "market_follow",
            "fixed_threshold",
        }
    finally:
        await _cleanup(session_factory, provider_code, experiment_ids)
        await engine.dispose()


async def _cleanup(
    session_factory,
    provider_code: str,
    experiment_ids: list[UUID],
) -> None:
    async with session_factory.begin() as session:
        portfolio_ids = select(PaperPortfolioModel.portfolio_id).where(
            PaperPortfolioModel.experiment_run_id.in_(experiment_ids)
        )
        decision_ids = select(TradeDecisionModel.decision_id).where(
            TradeDecisionModel.portfolio_id.in_(portfolio_ids)
        )
        order_ids = select(PaperOrderModel.order_id).where(
            PaperOrderModel.decision_id.in_(decision_ids)
        )
        trade_ids = select(PaperTradeModel.trade_id).where(PaperTradeModel.order_id.in_(order_ids))
        position_ids = select(PaperPositionModel.position_id).where(
            PaperPositionModel.trade_id.in_(trade_ids)
        )
        for model, condition in (
            (
                CommercialEvaluationModel,
                CommercialEvaluationModel.portfolio_id.in_(portfolio_ids),
            ),
            (
                PaperPerformanceSnapshotModel,
                PaperPerformanceSnapshotModel.portfolio_id.in_(portfolio_ids),
            ),
            (
                PaperLedgerEntryModel,
                PaperLedgerEntryModel.portfolio_id.in_(portfolio_ids),
            ),
            (
                PaperSettlementModel,
                PaperSettlementModel.position_id.in_(position_ids),
            ),
            (PaperPositionModel, PaperPositionModel.position_id.in_(position_ids)),
            (PaperTradeModel, PaperTradeModel.trade_id.in_(trade_ids)),
            (PaperOrderModel, PaperOrderModel.order_id.in_(order_ids)),
            (
                TradeDecisionModel,
                TradeDecisionModel.decision_id.in_(decision_ids),
            ),
            (
                PaperPortfolioModel,
                PaperPortfolioModel.portfolio_id.in_(portfolio_ids),
            ),
        ):
            await session.execute(delete(model).where(condition))

        prediction_ids = select(PredictionRunModel.prediction_run_id).where(
            PredictionRunModel.experiment_run_id.in_(experiment_ids)
        )
        await session.execute(
            delete(AgentPredictionModel).where(
                AgentPredictionModel.prediction_run_id.in_(prediction_ids)
            )
        )
        await session.execute(
            delete(PredictionRunModel).where(
                PredictionRunModel.experiment_run_id.in_(experiment_ids)
            )
        )
        provider_id = await session.scalar(
            select(ProviderModel.provider_id).where(ProviderModel.code == provider_code)
        )
        if provider_id is not None:
            market_ids = select(MarketModel.market_id).where(MarketModel.provider_id == provider_id)
            for model in (
                MarketObservationModel,
                MarketSnapshotModel,
                MarketStateChangeModel,
            ):
                await session.execute(delete(model).where(model.market_id.in_(market_ids)))
            await session.execute(delete(MarketModel).where(MarketModel.provider_id == provider_id))
            await session.execute(
                delete(ProviderModel).where(ProviderModel.provider_id == provider_id)
            )
        await session.execute(
            delete(CollectorCheckpointModel).where(
                CollectorCheckpointModel.provider_code == provider_code
            )
        )
        await session.execute(
            delete(CollectorRunModel).where(CollectorRunModel.provider_code == provider_code)
        )
        await session.execute(
            delete(ExperimentRunModel).where(
                ExperimentRunModel.experiment_run_id.in_(experiment_ids)
            )
        )
