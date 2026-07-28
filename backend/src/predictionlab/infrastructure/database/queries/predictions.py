"""SQLAlchemy prediction query adapter and post-resolution sample source."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from predictionlab.application.predictions import (
    AgentPredictionDetail,
    ListPredictions,
    PredictionRunDetail,
    PredictionRunPage,
    ResolvedPredictionSample,
)
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    Recommendation,
)
from predictionlab.domain.markets import ResolutionOutcome
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    MarketModel,
    PredictionRunModel,
)


class SqlAlchemyPredictionReadRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list(self, query: ListPredictions) -> PredictionRunPage:
        filters = _filters(query)
        async with self._session_factory() as session:
            total = (
                await session.scalar(
                    select(func.count())
                    .select_from(PredictionRunModel)
                    .join(MarketModel)
                    .where(*filters)
                )
                or 0
            )
            rows = (
                await session.execute(
                    select(PredictionRunModel, MarketModel)
                    .join(MarketModel)
                    .where(*filters)
                    .order_by(
                        PredictionRunModel.predicted_at.desc(),
                        PredictionRunModel.prediction_run_id.asc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
            agents = await _agents_for(
                session,
                tuple(row.PredictionRunModel.prediction_run_id for row in rows),
            )
        return PredictionRunPage(
            items=tuple(
                _detail(row.PredictionRunModel, row.MarketModel, agents)
                for row in rows
            ),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def get(self, prediction_id: UUID) -> PredictionRunDetail | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(PredictionRunModel, MarketModel)
                    .join(MarketModel)
                    .where(PredictionRunModel.prediction_run_id == prediction_id)
                )
            ).one_or_none()
            if row is None:
                return None
            agents = await _agents_for(session, (prediction_id,))
        return _detail(row.PredictionRunModel, row.MarketModel, agents)

    async def resolved_samples(
        self,
        *,
        experiment_run_id: UUID | None,
    ) -> tuple[ResolvedPredictionSample, ...]:
        filters: list[ColumnElement[bool]] = [
            MarketModel.resolution_outcome.in_(
                [ResolutionOutcome.YES.value, ResolutionOutcome.NO.value]
            )
        ]
        if experiment_run_id is not None:
            filters.append(
                PredictionRunModel.experiment_run_id == experiment_run_id
            )
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(PredictionRunModel, MarketModel)
                    .join(MarketModel)
                    .where(*filters)
                    .order_by(PredictionRunModel.predicted_at)
                )
            ).all()
        return tuple(
            ResolvedPredictionSample(
                prediction_run_id=row.PredictionRunModel.prediction_run_id,
                market_id=row.PredictionRunModel.market_id,
                predicted_at=row.PredictionRunModel.predicted_at,
                system_probability=row.PredictionRunModel.consensus_probability,
                market_probability=cast(
                    Decimal,
                    row.PredictionRunModel.market_probability,
                ),
                recommendation=Recommendation(
                    row.PredictionRunModel.recommendation
                ),
                status=PredictionRunStatus(row.PredictionRunModel.status),
                outcome=ResolutionOutcome(row.MarketModel.resolution_outcome),
            )
            for row in rows
            if row.PredictionRunModel.market_probability is not None
        )


def _filters(query: ListPredictions) -> tuple[ColumnElement[bool], ...]:
    filters: list[ColumnElement[bool]] = []
    if query.predicted_from is not None:
        filters.append(PredictionRunModel.predicted_at >= query.predicted_from)
    if query.predicted_to is not None:
        filters.append(PredictionRunModel.predicted_at <= query.predicted_to)
    if query.market_id is not None:
        filters.append(PredictionRunModel.market_id == query.market_id)
    if query.category is not None:
        filters.append(MarketModel.category == query.category.strip())
    if query.recommendation is not None:
        filters.append(
            PredictionRunModel.recommendation == query.recommendation.value
        )
    if query.status is not None:
        filters.append(PredictionRunModel.status == query.status.value)
    if query.opportunity_level is not None:
        filters.append(
            PredictionRunModel.opportunity_level == query.opportunity_level.value
        )
    if query.experiment_run_id is not None:
        filters.append(
            PredictionRunModel.experiment_run_id == query.experiment_run_id
        )
    return tuple(filters)


async def _agents_for(
    session: AsyncSession,
    run_ids: tuple[UUID, ...],
) -> dict[UUID, tuple[AgentPredictionDetail, ...]]:
    if not run_ids:
        return {}
    models = (
        await session.scalars(
            select(AgentPredictionModel)
            .where(AgentPredictionModel.prediction_run_id.in_(run_ids))
            .order_by(
                AgentPredictionModel.prediction_run_id,
                case(
                    {
                        "reasoning": 1,
                        "market": 2,
                        "skeptic": 3,
                        "consensus": 4,
                    },
                    value=AgentPredictionModel.agent_name,
                    else_=99,
                ),
            )
        )
    ).all()
    grouped: dict[UUID, list[AgentPredictionDetail]] = defaultdict(list)
    for model in models:
        grouped[model.prediction_run_id].append(_agent_detail(model))
    return {key: tuple(value) for key, value in grouped.items()}


def _detail(
    model: PredictionRunModel,
    market: MarketModel,
    agents: dict[UUID, tuple[AgentPredictionDetail, ...]],
) -> PredictionRunDetail:
    return PredictionRunDetail(
        prediction_run_id=model.prediction_run_id,
        experiment_run_id=model.experiment_run_id,
        market_id=model.market_id,
        market_title=market.title,
        category=market.category,
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
        agent_weights={
            key: Decimal(str(value)) for key, value in model.agent_weights.items()
        },
        agent_predictions=agents.get(model.prediction_run_id, ()),
    )


def _agent_detail(model: AgentPredictionModel) -> AgentPredictionDetail:
    return AgentPredictionDetail(
        agent_prediction_id=model.agent_prediction_id,
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
        agent_weights={
            key: Decimal(str(value)) for key, value in model.agent_weights.items()
        },
    )
