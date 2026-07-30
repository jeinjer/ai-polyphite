"""Durable prediction audit models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base
from predictionlab.infrastructure.database.models.markets import (
    PROBABILITY_PRECISION,
    PROBABILITY_SCALE,
)


class PredictionRunModel(Base):
    __tablename__ = "prediction_runs"
    __table_args__ = (
        UniqueConstraint(
            "experiment_run_id",
            "market_id",
            "predicted_at",
            "agent_configuration_hash",
            name="uq_prediction_runs_idempotency",
        ),
        Index(
            "uq_prediction_runs_live_idempotency",
            "market_id",
            "predicted_at",
            "agent_configuration_hash",
            unique=True,
            postgresql_where=text("experiment_run_id IS NULL"),
        ),
        CheckConstraint(
            "status IN ('predicted', 'completed', 'abstained', 'failed')",
            name="prediction_runs_valid_status",
        ),
        CheckConstraint(
            "estimated_outcome IS NULL OR estimated_outcome IN ('yes', 'no')",
            name="prediction_runs_valid_estimated_outcome",
        ),
        CheckConstraint(
            "recommendation IN ('yes', 'no', 'abstain')",
            name="prediction_runs_valid_recommendation",
        ),
        CheckConstraint(
            "opportunity_level IN ('none', 'weak', 'moderate', 'strong')",
            name="prediction_runs_valid_opportunity",
        ),
        CheckConstraint(
            "market_probability IS NULL OR (market_probability >= 0 AND market_probability <= 1)",
            name="prediction_runs_market_probability_range",
        ),
        CheckConstraint(
            "consensus_probability IS NULL OR "
            "(consensus_probability >= 0 AND consensus_probability <= 1)",
            name="prediction_runs_consensus_probability_range",
        ),
        CheckConstraint(
            "consensus_confidence >= 0 AND consensus_confidence <= 1",
            name="prediction_runs_confidence_range",
        ),
        CheckConstraint(
            "disagreement_score >= 0 AND disagreement_score <= 1",
            name="prediction_runs_disagreement_range",
        ),
        CheckConstraint(
            "duration_ms >= 0",
            name="prediction_runs_duration_non_negative",
        ),
        CheckConstraint(
            "(status IN ('predicted', 'completed') "
            "AND recommendation IN ('yes', 'no') "
            "AND consensus_probability IS NOT NULL AND edge IS NOT NULL "
            "AND safe_error_type IS NULL AND abstention_reason IS NULL "
            "AND (status = 'completed' OR estimated_outcome IS NOT NULL)) OR "
            "(status = 'abstained' AND recommendation = 'abstain' "
            "AND consensus_probability IS NULL AND edge IS NULL "
            "AND safe_error_type IS NULL AND abstention_reason IS NOT NULL) OR "
            "(status = 'failed' AND safe_error_type IS NOT NULL "
            "AND abstention_reason IS NULL)",
            name="prediction_runs_valid_terminal_state",
        ),
        Index(
            "ix_prediction_runs_market_predicted_at",
            "market_id",
            "predicted_at",
        ),
        Index(
            "ix_prediction_runs_experiment_predicted_at",
            "experiment_run_id",
            "predicted_at",
        ),
    )

    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    experiment_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiment_runs.experiment_run_id", ondelete="RESTRICT"),
    )
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    market_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    consensus_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    consensus_confidence: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    estimated_outcome: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    edge: Mapped[Decimal | None] = mapped_column(Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE))
    no_edge: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    opportunity_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    disagreement_score: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    agent_configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    safe_error_type: Mapped[str | None] = mapped_column(String(200))
    abstention_reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(200), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agent_weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    agent_predictions: Mapped[list[AgentPredictionModel]] = relationship(
        back_populates="prediction_run",
        lazy="raise",
        order_by="AgentPredictionModel.agent_prediction_id",
    )


class AgentPredictionModel(Base):
    __tablename__ = "agent_predictions"
    __table_args__ = (
        UniqueConstraint(
            "prediction_run_id",
            "agent_name",
            name="uq_agent_predictions_run_agent",
        ),
        CheckConstraint(
            "recommendation IN ('yes', 'no', 'abstain')",
            name="agent_predictions_valid_recommendation",
        ),
        CheckConstraint(
            "predicted_probability IS NULL OR "
            "(predicted_probability >= 0 AND predicted_probability <= 1)",
            name="agent_predictions_probability_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="agent_predictions_confidence_range",
        ),
        CheckConstraint(
            "disagreement_score IS NULL OR (disagreement_score >= 0 AND disagreement_score <= 1)",
            name="agent_predictions_disagreement_range",
        ),
        CheckConstraint(
            "duration_ms >= 0",
            name="agent_predictions_duration_non_negative",
        ),
        CheckConstraint(
            "(recommendation = 'abstain' AND predicted_probability IS NULL) OR "
            "(recommendation IN ('yes', 'no') AND predicted_probability IS NOT NULL)",
            name="agent_predictions_recommendation_probability",
        ),
        Index(
            "ix_agent_predictions_agent_name_version",
            "agent_name",
            "agent_version",
        ),
    )

    agent_prediction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("prediction_runs.prediction_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale_summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    disagreement_score: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    agent_weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    prediction_run: Mapped[PredictionRunModel] = relationship(
        back_populates="agent_predictions",
        lazy="raise",
    )
