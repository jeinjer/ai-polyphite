"""Post-resolution evaluation service; never used by prediction generation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from predictionlab.application.predictions.models import (
    CalibrationBucket,
    MetricSummary,
    PredictionEvaluationReport,
    ResolvedPredictionSample,
)
from predictionlab.application.predictions.repository import PredictionReadRepository
from predictionlab.domain.predictions import (
    ConstantBaseline,
    MarketBaseline,
    PredictionRunStatus,
    ProbabilityScore,
    score_probability,
)


class PredictionEvaluationService:
    def __init__(self, repository: PredictionReadRepository) -> None:
        self._repository = repository

    async def evaluate(
        self,
        *,
        experiment_run_id: UUID | None,
    ) -> PredictionEvaluationReport:
        samples = await self._repository.resolved_samples(
            experiment_run_id=experiment_run_id
        )
        emitted = [
            sample
            for sample in samples
            if sample.status
            in {PredictionRunStatus.PREDICTED, PredictionRunStatus.COMPLETED}
            and sample.system_probability is not None
        ]
        abstained_count = sum(
            sample.status is PredictionRunStatus.ABSTAINED for sample in samples
        )
        market = MarketBaseline()
        constant = ConstantBaseline()
        system_scores = [
            score_probability(sample.system_probability, sample.binary_outcome)
            for sample in emitted
            if sample.system_probability is not None
        ]
        market_scores = [
            score_probability(
                market.probability(sample.market_probability),
                sample.binary_outcome,
            )
            for sample in emitted
        ]
        constant_scores = [
            score_probability(
                constant.probability(sample.market_probability),
                sample.binary_outcome,
            )
            for sample in emitted
        ]
        denominator = len(emitted) + abstained_count
        return PredictionEvaluationReport(
            experiment_run_id=experiment_run_id,
            resolved_count=len(samples),
            emitted_count=len(emitted),
            abstained_count=abstained_count,
            coverage=(
                Decimal(len(emitted)) / Decimal(denominator)
                if denominator
                else Decimal("0")
            ),
            system=_summary(system_scores),
            market_baseline=_summary(market_scores),
            constant_baseline=_summary(constant_scores),
            calibration=_calibration(emitted),
        )


def _summary(scores: list[ProbabilityScore]) -> MetricSummary | None:
    if not scores:
        return None
    count = Decimal(len(scores))
    return MetricSummary(
        brier_score=sum((item.brier_score for item in scores), Decimal("0")) / count,
        log_loss=sum((item.log_loss for item in scores), Decimal("0")) / count,
        absolute_error=(
            sum((item.absolute_error for item in scores), Decimal("0")) / count
        ),
        directional_accuracy=(
            Decimal(sum(item.directionally_correct for item in scores)) / count
        ),
    )


def _calibration(
    samples: list[ResolvedPredictionSample],
) -> tuple[CalibrationBucket, ...]:
    grouped: dict[int, list[ResolvedPredictionSample]] = defaultdict(list)
    for sample in samples:
        assert sample.system_probability is not None
        index = min(int(sample.system_probability * Decimal("10")), 9)
        grouped[index].append(sample)
    result = []
    for index in sorted(grouped):
        items = grouped[index]
        count = Decimal(len(items))
        result.append(
            CalibrationBucket(
                lower_bound=Decimal(index) / Decimal("10"),
                upper_bound=Decimal(index + 1) / Decimal("10"),
                prediction_count=len(items),
                mean_probability=(
                    sum(
                        (
                            item.system_probability
                            for item in items
                            if item.system_probability is not None
                        ),
                        Decimal("0"),
                    )
                    / count
                ),
                observed_frequency=(
                    sum((item.binary_outcome for item in items), Decimal("0")) / count
                ),
            )
        )
    return tuple(result)
