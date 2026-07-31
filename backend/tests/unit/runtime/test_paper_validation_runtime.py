from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from predictionlab.application.paper_validation import (
    PaperValidationRunResult,
    PaperValidationRunStatus,
)
from predictionlab.runtime.paper_validation_runtime import _ParallelCampaignRunner

NOW = datetime(2026, 7, 31, 12, tzinfo=UTC)


class Campaign:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = 0

    async def run_cycle(
        self,
        *,
        scheduled_for: datetime,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> PaperValidationRunResult:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return PaperValidationRunResult(
            run_id=uuid4(),
            cycle_key="a" * 64,
            scheduled_for=scheduled_for,
            started_at=NOW,
            finished_at=NOW,
            duration_ms=0,
            status=PaperValidationRunStatus.COMPLETED,
            correlation_id=correlation_id or "test",
            causation_id=causation_id,
        )


@pytest.mark.asyncio
async def test_campaign_failure_does_not_prevent_other_campaigns() -> None:
    primary = Campaign(failure=RuntimeError("primary failed"))
    experimental = Campaign()
    runner = _ParallelCampaignRunner(primary, (experimental,))  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="primary failed"):
        await runner.run_cycle(scheduled_for=NOW)

    assert primary.calls == 1
    assert experimental.calls == 1


@pytest.mark.asyncio
async def test_primary_result_is_returned_after_all_campaigns_succeed() -> None:
    primary = Campaign()
    experimental = Campaign()
    runner = _ParallelCampaignRunner(primary, (experimental,))  # type: ignore[arg-type]

    result = await runner.run_cycle(scheduled_for=NOW)

    assert result.status is PaperValidationRunStatus.COMPLETED
    assert primary.calls == 1
    assert experimental.calls == 1
