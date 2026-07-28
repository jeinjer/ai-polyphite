from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Final
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from predictionlab.infrastructure.database.base import Base

PROBABILITY_PRECISION: Final = 12
PROBABILITY_SCALE: Final = 10
AMOUNT_PRECISION: Final = 28
AMOUNT_SCALE: Final = 8


class ProviderModel(Base):
    __tablename__ = "providers"
    __table_args__ = (
        CheckConstraint("char_length(code) > 0", name="code_not_blank"),
        CheckConstraint("char_length(name) > 0", name="name_not_blank"),
    )

    provider_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    markets: Mapped[list[MarketModel]] = relationship(
        back_populates="provider",
        lazy="raise",
    )


class MarketModel(Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "provider_market_id",
            name="uq_markets_provider_reference",
        ),
        CheckConstraint(
            "status IN ('open', 'closed', 'resolved', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint(
            "char_length(provider_market_id) > 0",
            name="provider_market_id_not_blank",
        ),
        CheckConstraint(
            "("
            "(status IN ('open', 'closed') AND resolution_outcome = 'unresolved') "
            "OR (status = 'resolved' AND resolution_outcome IN ('yes', 'no', 'other')) "
            "OR (status = 'cancelled' AND resolution_outcome = 'cancelled')"
            ")",
            name="market_resolution_coherent",
        ),
        CheckConstraint(
            "resolution_source IS NULL OR char_length(resolution_source) > 0",
            name="market_resolution_source_not_blank",
        ),
        CheckConstraint("char_length(title) > 0", name="title_not_blank"),
        Index("ix_markets_status", "status"),
        Index("ix_markets_resolution_at", "resolution_at"),
        Index("ix_markets_category", "category"),
    )

    market_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("providers.provider_id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_market_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(1_000), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(200))
    resolution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    provider: Mapped[ProviderModel] = relationship(
        back_populates="markets",
        lazy="raise",
    )
    snapshots: Mapped[list[MarketSnapshotModel]] = relationship(
        back_populates="market",
        lazy="raise",
        order_by="MarketSnapshotModel.observed_at",
    )
    observations: Mapped[list[MarketObservationModel]] = relationship(
        back_populates="market",
        lazy="raise",
        order_by="MarketObservationModel.observed_at",
    )
    state_history: Mapped[list[MarketStateChangeModel]] = relationship(
        back_populates="market",
        lazy="raise",
        order_by="MarketStateChangeModel.occurred_at",
    )

    resolution_outcome: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_source: Mapped[str | None] = mapped_column(String(200))


class MarketSnapshotModel(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "observed_at",
            name="uq_market_snapshots_market_observed_at",
        ),
        CheckConstraint(
            "yes_price >= 0 AND yes_price <= 1",
            name="yes_price_range",
        ),
        CheckConstraint(
            "no_price >= 0 AND no_price <= 1",
            name="no_price_range",
        ),
        CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="probability_range",
        ),
        CheckConstraint("spread >= 0 AND spread <= 1", name="spread_range"),
        CheckConstraint("volume >= 0", name="volume_non_negative"),
        CheckConstraint("liquidity >= 0", name="liquidity_non_negative"),
        Index(
            "ix_market_snapshots_market_observed_at",
            "market_id",
            "observed_at",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    yes_price: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    no_price: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    probability: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    spread: Mapped[Decimal] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
        nullable=False,
    )
    volume: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )
    liquidity: Mapped[Decimal] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
        nullable=False,
    )

    market: Mapped[MarketModel] = relationship(
        back_populates="snapshots",
        lazy="raise",
    )


class MarketObservationModel(Base):
    __tablename__ = "market_observations"
    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "observed_at",
            name="uq_market_observations_market_observed_at",
        ),
        CheckConstraint(
            "probability IS NULL OR (probability >= 0 AND probability <= 1)",
            name="market_observations_probability_range",
        ),
        CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="market_observations_volume_non_negative",
        ),
        CheckConstraint(
            "liquidity IS NULL OR liquidity >= 0",
            name="market_observations_liquidity_non_negative",
        ),
        CheckConstraint(
            "probability IS NOT NULL OR volume IS NOT NULL OR liquidity IS NOT NULL",
            name="market_observations_has_value",
        ),
        Index(
            "ix_market_observations_market_observed_at",
            "market_id",
            "observed_at",
        ),
        Index(
            "ix_market_observations_provider_observed_at",
            "provider_code",
            "observed_at",
        ),
    )

    observation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    probability: Mapped[Decimal | None] = mapped_column(
        Numeric(PROBABILITY_PRECISION, PROBABILITY_SCALE),
    )
    volume: Mapped[Decimal | None] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
    )
    liquidity: Mapped[Decimal | None] = mapped_column(
        Numeric(AMOUNT_PRECISION, AMOUNT_SCALE),
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    provider_code: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("providers.code", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64))

    market: Mapped[MarketModel] = relationship(
        back_populates="observations",
        lazy="raise",
    )


class MarketStateChangeModel(Base):
    __tablename__ = "market_state_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'closed', 'resolved', 'cancelled')",
            name="market_state_history_valid_status",
        ),
        CheckConstraint(
            "resolution_outcome IN ('unresolved', 'yes', 'no', 'cancelled', 'other')",
            name="market_state_history_valid_outcome",
        ),
        Index(
            "ix_market_state_history_market_occurred_at",
            "market_id",
            "occurred_at",
        ),
    )

    change_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    market_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("markets.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_resolution_outcome: Mapped[str | None] = mapped_column(String(32))
    resolution_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_source: Mapped[str | None] = mapped_column(String(200))

    market: Mapped[MarketModel] = relationship(
        back_populates="state_history",
        lazy="raise",
    )
