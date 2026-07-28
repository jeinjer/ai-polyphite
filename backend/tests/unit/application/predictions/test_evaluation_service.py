from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from predictionlab.application.predictions import PredictionEvaluationService
from predictionlab.application.predictions.models import ResolvedPredictionSample
from predictionlab.domain.agents import Recommendation
from predictionlab.domain.markets import ResolutionOutcome
from predictionlab.domain.predictions import PredictionRunStatus

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class SampleRepository:
    async def resolved_samples(self, *, experiment_run_id):
        return (
            ResolvedPredictionSample(
                prediction_run_id=uuid4(),
                market_id=uuid4(),
                predicted_at=NOW,
                system_probability=Decimal("0.80"),
                market_probability=Decimal("0.60"),
                recommendation=Recommendation.YES,
                status=PredictionRunStatus.COMPLETED,
                outcome=ResolutionOutcome.YES,
            ),
            ResolvedPredictionSample(
                prediction_run_id=uuid4(),
                market_id=uuid4(),
                predicted_at=NOW,
                system_probability=None,
                market_probability=Decimal("0.40"),
                recommendation=Recommendation.ABSTAIN,
                status=PredictionRunStatus.ABSTAINED,
                outcome=ResolutionOutcome.NO,
            ),
        )


@pytest.mark.asyncio
async def test_evaluation_separates_coverage_and_compares_baselines() -> None:
    report = await PredictionEvaluationService(SampleRepository()).evaluate(
        experiment_run_id=None
    )

    assert report.resolved_count == 2
    assert report.emitted_count == 1
    assert report.abstained_count == 1
    assert report.coverage == Decimal("0.5")
    assert report.system is not None
    assert report.market_baseline is not None
    assert report.constant_baseline is not None
    assert report.system.brier_score < report.market_baseline.brier_score
    assert report.calibration[0].prediction_count == 1
