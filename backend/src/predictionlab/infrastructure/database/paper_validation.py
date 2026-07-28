"""PostgreSQL audit, lock and accounting reconciliation for paper validation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from predictionlab.application.paper_validation import (
    CompletedPaperValidationCycle,
    PaperValidationRunResult,
    PaperValidationRunStarted,
    PortfolioReconciliation,
)
from predictionlab.core.hashing import canonical_sha256
from predictionlab.infrastructure.database.models import (
    PaperLedgerEntryModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperSettlementModel,
    PaperValidationRunModel,
)

_LOCK_KEY = "predictionlab:continuous-paper-validation"


class SqlAlchemyPaperValidationRunStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def start(self, run: PaperValidationRunStarted) -> None:
        async with self._session_factory.begin() as session:
            session.add(
                PaperValidationRunModel(
                    run_id=run.run_id,
                    cycle_key=run.cycle_key,
                    scheduled_for=run.scheduled_for,
                    started_at=run.started_at,
                    finished_at=None,
                    status="running",
                    portfolio_id=None,
                    prediction_count=0,
                    decision_count=0,
                    trade_count=0,
                    settlement_count=0,
                    reconciliation_ok=None,
                    reconciliation_details=None,
                    reconciliation_result_hash=None,
                    correlation_id=run.correlation_id,
                    causation_id=run.causation_id,
                    duration_ms=None,
                    safe_error_type=None,
                    result_hash=None,
                )
            )

    async def finish(self, result: PaperValidationRunResult) -> None:
        reconciliation = result.reconciliation
        async with self._session_factory.begin() as session:
            updated_id = await session.scalar(
                update(PaperValidationRunModel)
                .where(PaperValidationRunModel.run_id == result.run_id)
                .values(
                    finished_at=result.finished_at,
                    status=result.status.value,
                    portfolio_id=result.portfolio_id,
                    prediction_count=result.prediction_count,
                    decision_count=result.decision_count,
                    trade_count=result.trade_count,
                    settlement_count=result.settlement_count,
                    reconciliation_ok=(
                        reconciliation.is_consistent
                        if reconciliation is not None
                        else None
                    ),
                    reconciliation_details=(
                        reconciliation.audit_payload()
                        if reconciliation is not None
                        else None
                    ),
                    reconciliation_result_hash=(
                        reconciliation.result_hash
                        if reconciliation is not None
                        else None
                    ),
                    duration_ms=result.duration_ms,
                    safe_error_type=result.safe_error_type,
                    result_hash=result.result_hash,
                )
                .returning(PaperValidationRunModel.run_id)
            )
            if updated_id is None:
                raise RuntimeError("paper validation run disappeared before completion")

    async def find_completed(
        self,
        cycle_key: str,
    ) -> CompletedPaperValidationCycle | None:
        async with self._session_factory() as session:
            model = (
                await session.scalars(
                    select(PaperValidationRunModel)
                    .where(
                        PaperValidationRunModel.cycle_key == cycle_key,
                        PaperValidationRunModel.status == "completed",
                        PaperValidationRunModel.portfolio_id.is_not(None),
                        PaperValidationRunModel.reconciliation_result_hash.is_not(None),
                        PaperValidationRunModel.result_hash.is_not(None),
                    )
                    .order_by(
                        PaperValidationRunModel.finished_at.desc(),
                        PaperValidationRunModel.run_id,
                    )
                    .limit(1)
                )
            ).first()
        if model is None:
            return None
        assert model.portfolio_id is not None
        assert model.reconciliation_result_hash is not None
        assert model.result_hash is not None
        return CompletedPaperValidationCycle(
            run_id=model.run_id,
            portfolio_id=model.portfolio_id,
            prediction_count=model.prediction_count,
            decision_count=model.decision_count,
            trade_count=model.trade_count,
            settlement_count=model.settlement_count,
            reconciliation_result_hash=model.reconciliation_result_hash,
            result_hash=model.result_hash,
        )

    async def reconcile(
        self,
        portfolio_id: UUID,
        *,
        checked_at: datetime,
    ) -> PortfolioReconciliation:
        async with self._session_factory() as session:
            portfolio = await session.scalar(
                select(PaperPortfolioModel).where(
                    PaperPortfolioModel.portfolio_id == portfolio_id
                )
            )
            if portfolio is None:
                raise RuntimeError("paper portfolio disappeared before reconciliation")

            ledger = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(PaperLedgerEntryModel.amount), 0),
                        func.count().filter(
                            PaperLedgerEntryModel.entry_type == "initial_capital"
                        ),
                    ).where(PaperLedgerEntryModel.portfolio_id == portfolio_id)
                )
            ).one()
            positions = (
                await session.execute(
                    select(
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        PaperPositionModel.status == "open",
                                        PaperPositionModel.invested_amount,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        PaperPositionModel.status == "open",
                                        PaperPositionModel.unrealized_pnl,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                    ).where(PaperPositionModel.portfolio_id == portfolio_id)
                )
            ).one()
            realized = await session.scalar(
                select(func.coalesce(func.sum(PaperSettlementModel.realized_pnl), 0))
                .join(
                    PaperPositionModel,
                    PaperPositionModel.position_id
                    == PaperSettlementModel.position_id,
                )
                .where(PaperPositionModel.portfolio_id == portfolio_id)
            )

        expected_cash = Decimal(ledger[0] or 0)
        initial_entries = int(ledger[1] or 0)
        expected_reserved = Decimal(positions[0] or 0)
        expected_unrealized = Decimal(positions[1] or 0)
        expected_realized = Decimal(realized or 0)
        expected_equity = expected_cash + expected_reserved + expected_unrealized
        comparisons = {
            "initial_ledger_entry_count": initial_entries == 1,
            "ledger_cash_balance": expected_cash == portfolio.cash_balance,
            "open_position_reserve": expected_reserved
            == portfolio.reserved_balance,
            "settlement_realized_pnl": expected_realized == portfolio.realized_pnl,
            "open_position_unrealized_pnl": expected_unrealized
            == portfolio.unrealized_pnl,
            "portfolio_equity": expected_equity == portfolio.equity,
            "total_exposure": expected_reserved == portfolio.total_exposure,
        }
        discrepancy_codes = tuple(
            code for code, matches in comparisons.items() if not matches
        )
        payload = {
            "portfolio_id": portfolio_id,
            "checked_at": checked_at,
            "expected": {
                "cash_balance": expected_cash,
                "reserved_balance": expected_reserved,
                "realized_pnl": expected_realized,
                "unrealized_pnl": expected_unrealized,
                "equity": expected_equity,
                "total_exposure": expected_reserved,
                "initial_ledger_entries": initial_entries,
            },
            "actual": {
                "cash_balance": portfolio.cash_balance,
                "reserved_balance": portfolio.reserved_balance,
                "realized_pnl": portfolio.realized_pnl,
                "unrealized_pnl": portfolio.unrealized_pnl,
                "equity": portfolio.equity,
                "total_exposure": portfolio.total_exposure,
            },
            "discrepancy_codes": discrepancy_codes,
        }
        return PortfolioReconciliation(
            portfolio_id=portfolio_id,
            checked_at=checked_at,
            is_consistent=not discrepancy_codes,
            discrepancy_codes=discrepancy_codes,
            expected_cash_balance=expected_cash,
            actual_cash_balance=portfolio.cash_balance,
            expected_reserved_balance=expected_reserved,
            actual_reserved_balance=portfolio.reserved_balance,
            expected_realized_pnl=expected_realized,
            actual_realized_pnl=portfolio.realized_pnl,
            expected_unrealized_pnl=expected_unrealized,
            actual_unrealized_pnl=portfolio.unrealized_pnl,
            expected_equity=expected_equity,
            actual_equity=portfolio.equity,
            expected_total_exposure=expected_reserved,
            actual_total_exposure=portfolio.total_exposure,
            initial_ledger_entries=initial_entries,
            result_hash=canonical_sha256(payload),
        )


class PostgresPaperValidationLock:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[bool]:
        async with self._engine.connect() as connection, connection.begin():
            acquired = await connection.scalar(
                text(
                    "SELECT pg_try_advisory_xact_lock("
                    "hashtextextended(:lock_key, 0))"
                ),
                {"lock_key": _LOCK_KEY},
            )
            yield acquired is True
