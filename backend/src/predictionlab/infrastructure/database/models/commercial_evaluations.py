"""Durable commercial evaluations separated from prediction and execution."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base
from predictionlab.infrastructure.database.models.markets import (
    PROBABILITY_PRECISION,
    PROBABILITY_SCALE,
)


class CommercialEvaluationModel(Base):
    __tablename__ = "commercial_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "prediction_run_id",
            "portfolio_id",
            "campaign_id",
            "configuration_hash",
            name="uq_commercial_evaluations_scope",
        ),
        Index(
            "uq_commercial_evaluations_scope_without_portfolio",
            "prediction_run_id",
            "campaign_id",
            "configuration_hash",
            unique=True,
            postgresql_where=text("portfolio_id IS NULL"),
        ),
        CheckConstraint(
            "estimated_outcome IS NULL OR estimated_outcome IN ('yes', 'no')",
            name="commercial_evaluations_valid_estimated_outcome",
        ),
        CheckConstraint(
            "potential_side IN ('buy_yes', 'buy_no', 'none')",
            name="commercial_evaluations_valid_potential_side",
        ),
        CheckConstraint(
            "commercial_label IN "
            "('actionable', 'not_actionable', 'not_evaluable')",
            name="commercial_evaluations_valid_label",
        ),
        CheckConstraint(
            "data_freshness_status IN ('fresh', 'stale', 'unavailable')",
            name="commercial_evaluations_valid_freshness",
        ),
        CheckConstraint(
            "market_probability IS NULL OR "
            "(market_probability >= 0 AND market_probability <= 1)",
            name="commercial_evaluations_market_probability_range",
        ),
        CheckConstraint(
            "consensus_probability IS NULL OR "
            "(consensus_probability >= 0 AND consensus_probability <= 1)",
            name="commercial_evaluations_consensus_probability_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="commercial_evaluations_confidence_range",
        ),
        CheckConstraint(
            "gross_edge IS NULL OR (gross_edge >= -1 AND gross_edge <= 1)",
            name="commercial_evaluations_gross_edge_range",
        ),
        CheckConstraint(
            "net_edge IS NULL OR (net_edge >= -1 AND net_edge <= 1)",
            name="commercial_evaluations_net_edge_range",
        ),
        CheckConstraint(
            "estimated_fees >= 0 AND estimated_fees <= 1 "
            "AND estimated_slippage >= 0 AND estimated_slippage <= 1 "
            "AND estimated_other_costs >= 0 AND estimated_other_costs <= 1",
            name="commercial_evaluations_cost_range",
        ),
        CheckConstraint(
            "(commercial_label = 'actionable' AND is_actionable) OR "
            "(commercial_label <> 'actionable' AND NOT is_actionable)",
            name="commercial_evaluations_actionable_coherent",
        ),
        Index(
            "ix_commercial_evaluations_campaign_evaluated_at",
            "campaign_id",
            "evaluated_at",
        ),
        Index(
            "ix_commercial_evaluations_label_evaluated_at",
            "commercial_label",
            "evaluated_at",
        ),
        Index(
            "ix_commercial_evaluations_portfolio_evaluated_at",
            "portfolio_id",
            "evaluated_at",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    prediction_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("prediction_runs.prediction_run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    portfolio_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("paper_portfolios.portfolio_id", ondelete="RESTRICT"),
    )
    campaign_id: Mapped[str] = mapped_column(String(160), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    estimated_outcome: Mapped[str | None] = mapped_column(String(8))
    potential_side: Mapped[str] = mapped_column(String(16), nullable=False)
    market_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    consensus_probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    gross_edge: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    estimated_fees: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    estimated_slippage: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    estimated_other_costs: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    net_edge: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE)
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    commercial_label: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    is_actionable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    portfolio_has_open_position: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    data_freshness_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
