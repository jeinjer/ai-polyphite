"""Transactional PostgreSQL adapter for prediction aggregates."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from predictionlab.application.predictions.repository import (
    PredictionIdempotencyConflictError,
)
from predictionlab.domain.agents import (
    AgentEvidence,
    AgentPrediction,
    EvidenceDirection,
    Recommendation,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    OpportunityLevel,
    PredictionRun,
    PredictionRunStatus,
)
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    PredictionRunModel,
)


class SqlAlchemyPredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_if_absent(self, run: PredictionRun) -> PredictionRun:
        statement = insert(PredictionRunModel).values(**_run_values(run))
        if run.experiment_run_id is None:
            statement = statement.on_conflict_do_nothing(
                index_elements=(
                    PredictionRunModel.market_id,
                    PredictionRunModel.predicted_at,
                    PredictionRunModel.agent_configuration_hash,
                ),
                index_where=PredictionRunModel.experiment_run_id.is_(None),
            )
        else:
            statement = statement.on_conflict_do_nothing(
                constraint="uq_prediction_runs_idempotency"
            )
        inserted_id = await self._session.scalar(
            statement.returning(PredictionRunModel.prediction_run_id)
        )
        if inserted_id is None:
            existing = await self._session.scalar(
                select(PredictionRunModel).where(
                    PredictionRunModel.market_id == run.market_id,
                    PredictionRunModel.predicted_at == run.predicted_at,
                    PredictionRunModel.agent_configuration_hash == run.agent_configuration_hash,
                    (
                        PredictionRunModel.experiment_run_id.is_(None)
                        if run.experiment_run_id is None
                        else PredictionRunModel.experiment_run_id == run.experiment_run_id
                    ),
                )
            )
            if existing is None:
                raise RuntimeError("conflicting prediction disappeared before read")
            aggregate = await self._aggregate(existing)
            if aggregate.input_hash != run.input_hash or aggregate.result_hash != run.result_hash:
                raise PredictionIdempotencyConflictError(
                    "the idempotency scope already contains different prediction data"
                )
            return aggregate

        self._session.add_all(
            [
                AgentPredictionModel(
                    agent_prediction_id=uuid4(),
                    prediction_run_id=run.prediction_run_id,
                    agent_name=item.agent_name,
                    agent_version=item.agent_version,
                    predicted_probability=item.predicted_probability,
                    confidence=item.confidence,
                    recommendation=item.recommendation.value,
                    rationale_summary=item.rationale_summary,
                    evidence=[_evidence_json(value) for value in item.evidence],
                    warnings=list(item.warnings),
                    input_hash=item.input_hash,
                    output_hash=item.output_hash,
                    duration_ms=item.duration_ms,
                    disagreement_score=item.disagreement_score,
                    agent_weights={key: str(value) for key, value in item.agent_weights.items()},
                )
                for item in run.agent_predictions
            ]
        )
        await self._session.flush()
        return run

    async def _aggregate(self, model: PredictionRunModel) -> PredictionRun:
        agents = (
            await self._session.scalars(
                select(AgentPredictionModel)
                .where(AgentPredictionModel.prediction_run_id == model.prediction_run_id)
                .order_by(
                    case(
                        {
                            "reasoning": 1,
                            "market": 2,
                            "skeptic": 3,
                            "consensus": 4,
                        },
                        value=AgentPredictionModel.agent_name,
                        else_=99,
                    )
                )
            )
        ).all()
        return _run_entity(model, agents)


def _run_values(run: PredictionRun) -> dict[str, object]:
    return {
        "prediction_run_id": run.prediction_run_id,
        "experiment_run_id": run.experiment_run_id,
        "market_id": run.market_id,
        "predicted_at": run.predicted_at,
        "market_probability": run.market_probability,
        "consensus_probability": run.consensus_probability,
        "consensus_confidence": run.consensus_confidence,
        "recommendation": run.recommendation.value,
        "estimated_outcome": (
            run.estimated_outcome.value if run.estimated_outcome is not None else None
        ),
        "edge": run.edge,
        "no_edge": run.no_edge,
        "opportunity_level": run.opportunity_level.value,
        "disagreement_score": run.disagreement_score,
        "status": run.status.value,
        "agent_configuration_hash": run.agent_configuration_hash,
        "input_hash": run.input_hash,
        "result_hash": run.result_hash,
        "duration_ms": run.duration_ms,
        "safe_error_type": run.safe_error_type,
        "abstention_reason": run.abstention_reason,
        "correlation_id": run.correlation_id,
        "causation_id": run.causation_id,
        "created_at": run.created_at,
        "agent_weights": {key: str(value) for key, value in run.agent_weights.items()},
    }


def _evidence_json(value: AgentEvidence) -> dict[str, str]:
    return {
        "code": value.code,
        "summary": value.summary,
        "direction": value.direction.value,
        "strength": str(value.strength),
    }


def _run_entity(
    model: PredictionRunModel,
    agents: Sequence[AgentPredictionModel],
) -> PredictionRun:
    return PredictionRun(
        prediction_run_id=model.prediction_run_id,
        experiment_run_id=model.experiment_run_id,
        market_id=model.market_id,
        predicted_at=model.predicted_at,
        market_probability=model.market_probability,
        consensus_probability=model.consensus_probability,
        consensus_confidence=model.consensus_confidence,
        recommendation=Recommendation(model.recommendation),
        edge=model.edge,
        no_edge=model.no_edge,
        opportunity_level=OpportunityLevel(model.opportunity_level),
        disagreement_score=model.disagreement_score,
        status=PredictionRunStatus(model.status),
        agent_configuration_hash=model.agent_configuration_hash,
        input_hash=model.input_hash,
        result_hash=model.result_hash,
        duration_ms=model.duration_ms,
        safe_error_type=model.safe_error_type,
        abstention_reason=model.abstention_reason,
        correlation_id=model.correlation_id,
        causation_id=model.causation_id,
        created_at=model.created_at,
        agent_weights={key: Decimal(str(value)) for key, value in model.agent_weights.items()},
        agent_predictions=tuple(_agent_entity(item) for item in agents),
        estimated_outcome=(
            EstimatedOutcome(model.estimated_outcome)
            if model.estimated_outcome is not None
            else None
        ),
    )


def _agent_entity(model: AgentPredictionModel) -> AgentPrediction:
    return AgentPrediction(
        agent_name=model.agent_name,
        agent_version=model.agent_version,
        predicted_probability=model.predicted_probability,
        confidence=model.confidence,
        recommendation=Recommendation(model.recommendation),
        rationale_summary=model.rationale_summary,
        evidence=tuple(
            AgentEvidence(
                code=str(item["code"]),
                summary=str(item["summary"]),
                direction=EvidenceDirection(str(item["direction"])),
                strength=Decimal(str(item["strength"])),
            )
            for item in model.evidence
        ),
        warnings=tuple(model.warnings),
        input_hash=model.input_hash,
        output_hash=model.output_hash,
        duration_ms=model.duration_ms,
        disagreement_score=model.disagreement_score,
        agent_weights={key: Decimal(str(value)) for key, value in model.agent_weights.items()},
    )
