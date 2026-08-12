"""SQLAlchemy prediction query adapter and post-resolution sample source."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import ColumnElement

from predictionlab.application.predictions import (
    AgentPredictionDetail,
    ListPredictions,
    PredictionListItem,
    PredictionListPage,
    PredictionRunDetail,
    PredictionRunPage,
    PredictionSort,
    RelatedPaperExecution,
    ResolvedPredictionSample,
    SortDirection,
)
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    Recommendation,
)
from predictionlab.domain.commercial_evaluations import (
    CommercialEvaluation,
    CommercialLabel,
    DataFreshnessStatus,
    PotentialSide,
)
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome
from predictionlab.domain.paper_trading import (
    PositionSide,
    TradeDecisionSource,
    TradeDecisionType,
)
from predictionlab.domain.predictions import (
    EstimatedOutcome,
    OpportunityLevel,
    PredictionRunStatus,
)
from predictionlab.infrastructure.database.models import (
    AgentPredictionModel,
    CommercialEvaluationModel,
    MarketModel,
    PaperOrderModel,
    PaperPortfolioModel,
    PaperPositionModel,
    PaperTradeModel,
    PredictionRunModel,
    ProviderModel,
    TradeDecisionModel,
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
            items=tuple(_detail(row.PredictionRunModel, row.MarketModel, agents) for row in rows),
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def list_summary(
        self,
        query: ListPredictions,
    ) -> PredictionListPage:
        evaluation_query = select(
            CommercialEvaluationModel,
            func.row_number()
            .over(
                partition_by=CommercialEvaluationModel.prediction_run_id,
                order_by=(
                    _campaign_priority(CommercialEvaluationModel.campaign_id),
                    CommercialEvaluationModel.evaluated_at.desc(),
                    CommercialEvaluationModel.evaluation_id.asc(),
                ),
            )
            .label("evaluation_rank"),
        )
        if query.portfolio_id is not None:
            evaluation_query = evaluation_query.where(
                CommercialEvaluationModel.portfolio_id == query.portfolio_id
            )
        if query.campaign_id is not None:
            evaluation_query = evaluation_query.where(
                CommercialEvaluationModel.campaign_id == query.campaign_id.strip()
            )
        evaluation_subquery = evaluation_query.subquery()
        evaluation = aliased(
            CommercialEvaluationModel,
            evaluation_subquery,
        )
        join_condition = (evaluation.prediction_run_id == PredictionRunModel.prediction_run_id) & (
            evaluation_subquery.c.evaluation_rank == 1
        )
        filters = _summary_filters(query, evaluation)
        base = (
            select(
                PredictionRunModel,
                MarketModel,
                ProviderModel,
                evaluation,
            )
            .select_from(PredictionRunModel)
            .join(
                MarketModel,
                MarketModel.market_id == PredictionRunModel.market_id,
            )
            .join(
                ProviderModel,
                ProviderModel.provider_id == MarketModel.provider_id,
            )
            .outerjoin(evaluation, join_condition)
            .where(*filters)
        )
        sort_column = {
            PredictionSort.PREDICTED_AT: PredictionRunModel.predicted_at,
            PredictionSort.MARKET_PROBABILITY: (PredictionRunModel.market_probability),
            PredictionSort.CONSENSUS_PROBABILITY: (PredictionRunModel.consensus_probability),
            PredictionSort.CONSENSUS_CONFIDENCE: (PredictionRunModel.consensus_confidence),
            PredictionSort.NET_EDGE: evaluation.net_edge,
        }[query.sort]
        ordered = (
            sort_column.asc() if query.direction is SortDirection.ASC else sort_column.desc()
        ).nulls_last()
        async with self._session_factory() as session:
            total = (
                await session.scalar(
                    select(func.count()).select_from(base.order_by(None).subquery())
                )
                or 0
            )
            rows = (
                await session.execute(
                    base.order_by(
                        ordered,
                        PredictionRunModel.prediction_run_id.asc(),
                    )
                    .offset((query.page - 1) * query.page_size)
                    .limit(query.page_size)
                )
            ).all()
        return PredictionListPage(
            items=tuple(
                _list_item(prediction, market, provider, current_evaluation)
                for (
                    prediction,
                    market,
                    provider,
                    current_evaluation,
                ) in rows
            ),
            page=query.page,
            page_size=query.page_size,
            total_items=total,
            applied_filters=_applied_filters(query),
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
            evaluation = await session.scalar(
                select(CommercialEvaluationModel)
                .where(CommercialEvaluationModel.prediction_run_id == prediction_id)
                .order_by(
                    _campaign_priority(CommercialEvaluationModel.campaign_id),
                    CommercialEvaluationModel.evaluated_at.desc(),
                    CommercialEvaluationModel.evaluation_id.asc(),
                )
                .limit(1)
            )
            provider_code = await session.scalar(
                select(ProviderModel.code).where(
                    ProviderModel.provider_id == row.MarketModel.provider_id
                )
            )
            execution_rows = (
                await session.execute(
                    select(
                        TradeDecisionModel,
                        PaperPortfolioModel,
                        PaperOrderModel,
                        PaperTradeModel,
                        PaperPositionModel,
                    )
                    .join(
                        PaperPortfolioModel,
                        PaperPortfolioModel.portfolio_id == TradeDecisionModel.portfolio_id,
                    )
                    .outerjoin(
                        PaperOrderModel,
                        PaperOrderModel.decision_id == TradeDecisionModel.decision_id,
                    )
                    .outerjoin(
                        PaperTradeModel,
                        PaperTradeModel.order_id == PaperOrderModel.order_id,
                    )
                    .outerjoin(
                        PaperPositionModel,
                        PaperPositionModel.trade_id == PaperTradeModel.trade_id,
                    )
                    .where(TradeDecisionModel.prediction_run_id == prediction_id)
                    .order_by(
                        TradeDecisionModel.decided_at,
                        TradeDecisionModel.decision_id,
                    )
                )
            ).all()
        return _detail(
            row.PredictionRunModel,
            row.MarketModel,
            agents,
            evaluation=evaluation,
            provider_code=provider_code,
            related_executions=tuple(
                RelatedPaperExecution(
                    decision_id=decision.decision_id,
                    portfolio_id=portfolio.portfolio_id,
                    portfolio_name=portfolio.name,
                    decision=TradeDecisionType(decision.decision),
                    decision_source=TradeDecisionSource(decision.decision_source),
                    override_reason=decision.override_reason,
                    side=(PositionSide(decision.side) if decision.side is not None else None),
                    decided_at=decision.decided_at,
                    order_id=(order.order_id if order is not None else None),
                    trade_id=(trade.trade_id if trade is not None else None),
                    position_id=(position.position_id if position is not None else None),
                )
                for (
                    decision,
                    portfolio,
                    order,
                    trade,
                    position,
                ) in execution_rows
            ),
        )

    async def resolved_samples(
        self,
        *,
        experiment_run_id: UUID | None,
    ) -> tuple[ResolvedPredictionSample, ...]:
        filters: list[ColumnElement[bool]] = [
            MarketModel.resolution_outcome.in_(
                [ResolutionOutcome.YES.value, ResolutionOutcome.NO.value]
            ),
            MarketModel.resolved_at.is_not(None),
            PredictionRunModel.predicted_at <= MarketModel.resolved_at,
        ]
        if experiment_run_id is not None:
            filters.append(PredictionRunModel.experiment_run_id == experiment_run_id)
        ranked = (
            select(
                PredictionRunModel.prediction_run_id.label("prediction_run_id"),
                func.row_number()
                .over(
                    partition_by=PredictionRunModel.market_id,
                    order_by=(
                        PredictionRunModel.predicted_at.desc(),
                        PredictionRunModel.prediction_run_id.desc(),
                    ),
                )
                .label("prediction_rank"),
            )
            .join(MarketModel)
            .where(*filters)
            .subquery()
        )
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(PredictionRunModel, MarketModel)
                    .join(MarketModel)
                    .join(
                        ranked,
                        ranked.c.prediction_run_id
                        == PredictionRunModel.prediction_run_id,
                    )
                    .where(ranked.c.prediction_rank == 1)
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
                recommendation=Recommendation(row.PredictionRunModel.recommendation),
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
        filters.append(PredictionRunModel.recommendation == query.recommendation.value)
    if query.status is not None:
        filters.append(PredictionRunModel.status == query.status.value)
    if query.opportunity_level is not None:
        filters.append(PredictionRunModel.opportunity_level == query.opportunity_level.value)
    if query.experiment_run_id is not None:
        filters.append(PredictionRunModel.experiment_run_id == query.experiment_run_id)
    return tuple(filters)


def _summary_filters(
    query: ListPredictions,
    evaluation: type[CommercialEvaluationModel],
) -> tuple[ColumnElement[bool], ...]:
    filters = list(_filters(query))
    if query.portfolio_id is not None or query.campaign_id is not None:
        filters.append(evaluation.evaluation_id.is_not(None))
    if query.provider is not None:
        filters.append(ProviderModel.code == query.provider.strip())
    if query.commercial_label is CommercialLabel.NOT_EVALUABLE:
        filters.append(
            or_(
                evaluation.evaluation_id.is_(None),
                evaluation.commercial_label == CommercialLabel.NOT_EVALUABLE.value,
            )
        )
    elif query.commercial_label is not None:
        filters.append(evaluation.commercial_label == query.commercial_label.value)
    if query.estimated_outcome_filter is not None:
        if query.estimated_outcome_filter.value == "unavailable":
            filters.append(PredictionRunModel.estimated_outcome.is_(None))
        else:
            filters.append(
                PredictionRunModel.estimated_outcome == query.estimated_outcome_filter.value
            )
    return tuple(filters)


def _campaign_priority(
    column: ColumnElement[str] | InstrumentedAttribute[str],
) -> ColumnElement[int]:
    """Prefer the default automatic campaign unless a filter selects another."""

    return case(
        (column == "conservative-v1", 0),
        (column == "experimental-v1", 1),
        else_=2,
    )


def _applied_filters(query: ListPredictions) -> dict[str, str]:
    values = {
        "provider": query.provider,
        "category": query.category,
        "commercial_label": (
            query.commercial_label.value if query.commercial_label is not None else None
        ),
        "estimated_outcome": (
            query.estimated_outcome_filter.value
            if query.estimated_outcome_filter is not None
            else None
        ),
        "portfolio_id": (str(query.portfolio_id) if query.portfolio_id is not None else None),
        "campaign_id": query.campaign_id,
        "date_from": (
            query.predicted_from.isoformat() if query.predicted_from is not None else None
        ),
        "date_to": (query.predicted_to.isoformat() if query.predicted_to is not None else None),
        "sort": query.sort.value,
        "direction": query.direction.value,
    }
    return {key: value for key, value in values.items() if value is not None}


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
    *,
    evaluation: CommercialEvaluationModel | None = None,
    provider_code: str | None = None,
    related_executions: tuple[RelatedPaperExecution, ...] = (),
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
        agent_weights={key: Decimal(str(value)) for key, value in model.agent_weights.items()},
        agent_predictions=agents.get(model.prediction_run_id, ()),
        estimated_outcome=(
            EstimatedOutcome(model.estimated_outcome)
            if model.estimated_outcome is not None
            else None
        ),
        market_status=MarketStatus(market.status),
        provider_code=provider_code,
        commercial_evaluation=(
            _commercial_evaluation(evaluation) if evaluation is not None else None
        ),
        related_executions=related_executions,
    )


def _list_item(
    prediction: PredictionRunModel,
    market: MarketModel,
    provider: ProviderModel,
    evaluation: CommercialEvaluationModel | None,
) -> PredictionListItem:
    if evaluation is None:
        commercial_label = CommercialLabel.NOT_EVALUABLE
        potential_side = PotentialSide.NONE
        primary_reason = "legacy_prediction_without_commercial_evaluation"
        freshness = DataFreshnessStatus.UNAVAILABLE
    else:
        commercial_label = CommercialLabel(evaluation.commercial_label)
        potential_side = PotentialSide(evaluation.potential_side)
        primary_reason = (
            str(evaluation.reasons[0])
            if evaluation.reasons
            else "commercial_evaluation_unavailable"
        )
        freshness = DataFreshnessStatus(evaluation.data_freshness_status)
    return PredictionListItem(
        prediction_run_id=prediction.prediction_run_id,
        market_id=prediction.market_id,
        market_title=market.title,
        provider_code=provider.code,
        category=market.category,
        predicted_at=prediction.predicted_at,
        market_probability=prediction.market_probability,
        consensus_probability=prediction.consensus_probability,
        consensus_confidence=prediction.consensus_confidence,
        estimated_outcome=(
            EstimatedOutcome(prediction.estimated_outcome)
            if prediction.estimated_outcome is not None
            else None
        ),
        commercial_label=commercial_label,
        potential_side=potential_side,
        gross_edge=(evaluation.gross_edge if evaluation is not None else None),
        net_edge=evaluation.net_edge if evaluation is not None else None,
        is_actionable=(evaluation.is_actionable if evaluation is not None else False),
        primary_reason=primary_reason,
        portfolio_has_open_position=(
            evaluation.portfolio_has_open_position if evaluation is not None else False
        ),
        data_freshness_status=freshness,
        campaign_id=(evaluation.campaign_id if evaluation is not None else None),
        portfolio_id=(evaluation.portfolio_id if evaluation is not None else None),
    )


def _commercial_evaluation(
    model: CommercialEvaluationModel,
) -> CommercialEvaluation:
    return CommercialEvaluation(
        evaluation_id=model.evaluation_id,
        prediction_run_id=model.prediction_run_id,
        portfolio_id=model.portfolio_id,
        campaign_id=model.campaign_id,
        evaluated_at=model.evaluated_at,
        estimated_outcome=(
            EstimatedOutcome(model.estimated_outcome)
            if model.estimated_outcome is not None
            else None
        ),
        potential_side=PotentialSide(model.potential_side),
        market_probability=model.market_probability,
        consensus_probability=model.consensus_probability,
        gross_edge=model.gross_edge,
        estimated_fees=model.estimated_fees,
        estimated_slippage=model.estimated_slippage,
        estimated_other_costs=model.estimated_other_costs,
        net_edge=model.net_edge,
        confidence=model.confidence,
        commercial_label=CommercialLabel(model.commercial_label),
        is_actionable=model.is_actionable,
        reasons=tuple(model.reasons),
        warnings=tuple(model.warnings),
        configuration_hash=model.configuration_hash,
        result_hash=model.result_hash,
        created_at=model.created_at,
        portfolio_has_open_position=model.portfolio_has_open_position,
        data_freshness_status=DataFreshnessStatus(model.data_freshness_status),
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
        agent_weights={key: Decimal(str(value)) for key, value in model.agent_weights.items()},
    )
