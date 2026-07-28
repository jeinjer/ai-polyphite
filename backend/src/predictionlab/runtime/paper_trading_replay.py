"""Replay hook composing predictions, simulated trades and settlements."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from predictionlab.application.paper_trading import (
    CreatePaperPortfolio,
    PaperTradingOrchestrator,
    SettlePaperPortfolio,
)
from predictionlab.domain.paper_trading import CurrencyUnit
from predictionlab.runtime.prediction_replay import PredictionReplayHook


class PaperTradingReplayHook:
    def __init__(
        self,
        *,
        prediction_hook: PredictionReplayHook,
        orchestrator: PaperTradingOrchestrator,
        dataset_id: str,
        currency_unit: CurrencyUnit,
        initial_balance: Decimal,
    ) -> None:
        self._prediction_hook = prediction_hook
        self._orchestrator = orchestrator
        self._dataset_id = dataset_id
        self._currency_unit = currency_unit
        self._initial_balance = initial_balance
        self.portfolio_id: UUID | None = None
        self.decision_count = 0
        self.trade_count = 0
        self.settlement_count = 0
        self.final_equity = initial_balance
        self.final_result_hash: str | None = None

    @property
    def prediction_count(self) -> int:
        return self._prediction_hook.prediction_count

    @property
    def configuration_hash(self) -> str:
        return self._orchestrator.configuration_hash

    async def __call__(
        self,
        experiment_run_id: UUID,
        visible_at: datetime,
        correlation_id: str,
    ) -> tuple[str, ...]:
        prediction_hashes = await self._prediction_hook(
            experiment_run_id,
            visible_at,
            correlation_id,
        )
        if self.portfolio_id is None:
            portfolio_result = await self._orchestrator.create_portfolio(
                CreatePaperPortfolio(
                    name=f"Replay {self._dataset_id} — AI-Polyphite",
                    currency_unit=self._currency_unit,
                    initial_balance=self._initial_balance,
                    experiment_run_id=experiment_run_id,
                    correlation_id=correlation_id,
                    causation_id=f"replay-trade:{visible_at.isoformat()}",
                )
            )
            self.portfolio_id = portfolio_result.portfolio.portfolio_id
        outcomes = await self._orchestrator.run_batch(
            portfolio_id=self.portfolio_id,
            prediction_run_ids=tuple(
                run.prediction_run_id
                for run in self._prediction_hook.last_prediction_runs
            ),
            correlation_id=correlation_id,
            causation_id=f"replay-trade:{visible_at.isoformat()}",
        )
        settlement_batch = await self._orchestrator.settle(
            SettlePaperPortfolio(
                portfolio_id=self.portfolio_id,
                settled_at=visible_at,
                correlation_id=correlation_id,
                causation_id=f"replay-settle:{visible_at.isoformat()}",
            )
        )
        self.decision_count += len(outcomes)
        self.trade_count += sum(item.trade is not None for item in outcomes)
        self.settlement_count += len(settlement_batch.settlements)
        self.final_equity = settlement_batch.performance_snapshot.equity
        self.final_result_hash = settlement_batch.performance_snapshot.result_hash
        return (
            *prediction_hashes,
            *(value for outcome in outcomes for value in outcome.artifact_hashes),
            *settlement_batch.artifact_hashes,
        )
