"""Application models for continuous simulated validation cycles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PaperValidationRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_LOCKED = "skipped_locked"
    SKIPPED_COMPLETED = "skipped_completed"


@dataclass(frozen=True, slots=True)
class PaperValidationRunStarted:
    run_id: UUID
    cycle_key: str
    scheduled_for: datetime
    started_at: datetime
    correlation_id: str
    causation_id: str | None


@dataclass(frozen=True, slots=True)
class CompletedPaperValidationCycle:
    run_id: UUID
    portfolio_id: UUID
    prediction_count: int
    decision_count: int
    trade_count: int
    settlement_count: int
    reconciliation_result_hash: str
    result_hash: str


@dataclass(frozen=True, slots=True)
class PortfolioReconciliation:
    portfolio_id: UUID
    checked_at: datetime
    is_consistent: bool
    discrepancy_codes: tuple[str, ...]
    expected_cash_balance: Decimal
    actual_cash_balance: Decimal
    expected_reserved_balance: Decimal
    actual_reserved_balance: Decimal
    expected_realized_pnl: Decimal
    actual_realized_pnl: Decimal
    expected_unrealized_pnl: Decimal
    actual_unrealized_pnl: Decimal
    expected_equity: Decimal
    actual_equity: Decimal
    expected_total_exposure: Decimal
    actual_total_exposure: Decimal
    initial_ledger_entries: int
    result_hash: str

    def audit_payload(self) -> dict[str, str | bool | int | list[str]]:
        return {
            "portfolio_id": str(self.portfolio_id),
            "checked_at": self.checked_at.isoformat(),
            "is_consistent": self.is_consistent,
            "discrepancy_codes": list(self.discrepancy_codes),
            "expected_cash_balance": str(self.expected_cash_balance),
            "actual_cash_balance": str(self.actual_cash_balance),
            "expected_reserved_balance": str(self.expected_reserved_balance),
            "actual_reserved_balance": str(self.actual_reserved_balance),
            "expected_realized_pnl": str(self.expected_realized_pnl),
            "actual_realized_pnl": str(self.actual_realized_pnl),
            "expected_unrealized_pnl": str(self.expected_unrealized_pnl),
            "actual_unrealized_pnl": str(self.actual_unrealized_pnl),
            "expected_equity": str(self.expected_equity),
            "actual_equity": str(self.actual_equity),
            "expected_total_exposure": str(self.expected_total_exposure),
            "actual_total_exposure": str(self.actual_total_exposure),
            "initial_ledger_entries": self.initial_ledger_entries,
            "result_hash": self.result_hash,
        }


@dataclass(frozen=True, slots=True)
class PaperValidationRunResult:
    run_id: UUID
    cycle_key: str
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime
    duration_ms: Decimal
    status: PaperValidationRunStatus
    correlation_id: str
    causation_id: str | None
    portfolio_id: UUID | None = None
    prediction_count: int = 0
    decision_count: int = 0
    trade_count: int = 0
    settlement_count: int = 0
    reconciliation: PortfolioReconciliation | None = None
    safe_error_type: str | None = None
    result_hash: str | None = None
