from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from predictionlab.application.markets.errors import MarketNotFoundError
from predictionlab.application.markets.queries import (
    ListMarketHistory,
    ListMarketObservations,
    ListMarkets,
    MarketDetail,
    MarketHistoryEvent,
    MarketHistoryEventType,
    MarketHistoryPage,
    MarketObservationPage,
    MarketOrderField,
    MarketPage,
    MarketSummary,
    ObservationSummary,
    ProviderSummary,
    SnapshotSummary,
    SortDirection,
)
from predictionlab.application.markets.query_service import MarketQueryService
from predictionlab.domain.markets import MarketStatus, ResolutionOutcome

router = APIRouter(prefix="/markets", tags=["markets"])


class ProviderResponse(BaseModel):
    provider_id: UUID
    code: str
    name: str
    enabled: bool


class SnapshotResponse(BaseModel):
    snapshot_id: UUID
    observed_at: datetime
    yes_price: Decimal = Field(ge=0, le=1)
    no_price: Decimal = Field(ge=0, le=1)
    probability: Decimal = Field(ge=0, le=1)
    spread: Decimal = Field(ge=0, le=1)
    volume: Decimal = Field(ge=0)
    liquidity: Decimal = Field(ge=0)


class ObservationResponse(BaseModel):
    observation_id: UUID
    observed_at: datetime
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    liquidity: Decimal | None = Field(default=None, ge=0)
    source_updated_at: datetime | None
    ingested_at: datetime
    provider_code: str


class MarketSummaryResponse(BaseModel):
    market_id: UUID
    provider_market_id: str
    title: str
    category: str | None
    resolution_at: datetime | None
    source_created_at: datetime | None
    status: MarketStatus
    ingested_at: datetime
    updated_at: datetime
    provider: ProviderResponse
    latest_snapshot: SnapshotResponse | None
    resolution_outcome: ResolutionOutcome
    resolved_at: datetime | None
    resolution_source: str | None
    latest_observation: ObservationResponse | None
    probability_change: Decimal | None


class MarketDetailResponse(MarketSummaryResponse):
    description: str | None


class MarketPageResponse(BaseModel):
    items: list[MarketSummaryResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class ObservationPageResponse(BaseModel):
    items: list[ObservationResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=500)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class MarketHistoryEventResponse(BaseModel):
    event_id: str
    event_type: MarketHistoryEventType
    occurred_at: datetime
    previous_status: MarketStatus | None
    status: MarketStatus | None
    resolution_outcome: ResolutionOutcome | None
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    liquidity: Decimal | None = Field(default=None, ge=0)
    source: str | None


class MarketHistoryPageResponse(BaseModel):
    items: list[MarketHistoryEventResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=500)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


def get_market_query_service(request: Request) -> MarketQueryService:
    return cast(MarketQueryService, request.app.state.market_query_service)


@router.get(
    "",
    response_model=MarketPageResponse,
    summary="List markets",
    description=(
        "Returns a deterministic page of markets with provider metadata and "
        "their latest snapshot. All filters are combined with AND."
    ),
    operation_id="list_markets",
)
async def list_markets(
    service: Annotated[MarketQueryService, Depends(get_market_query_service)],
    page: Annotated[int, Query(ge=1, description="One-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Markets returned per page."),
    ] = 20,
    market_status: Annotated[
        MarketStatus | None,
        Query(alias="status", description="Exact market lifecycle status."),
    ] = None,
    provider: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=64,
            description="Exact provider code.",
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="Exact market category.",
        ),
    ] = None,
    order_by: Annotated[
        MarketOrderField,
        Query(description="Field used for deterministic ordering."),
    ] = MarketOrderField.UPDATED_AT,
    direction: Annotated[
        SortDirection,
        Query(description="Ascending or descending ordering."),
    ] = SortDirection.DESC,
) -> MarketPageResponse:
    result = await service.list(
        ListMarkets(
            page=page,
            page_size=page_size,
            status=market_status,
            provider_code=provider,
            category=category,
            order_by=order_by,
            direction=direction,
        )
    )
    return _page_response(result)


@router.get(
    "/{market_id}/observations",
    response_model=ObservationPageResponse,
    summary="List normalized market observations",
    operation_id="list_market_observations",
)
async def list_market_observations(
    market_id: UUID,
    service: Annotated[MarketQueryService, Depends(get_market_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
    observed_from: Annotated[
        datetime | None,
        Query(alias="from"),
    ] = None,
    observed_to: Annotated[
        datetime | None,
        Query(alias="to"),
    ] = None,
) -> ObservationPageResponse:
    try:
        result = await service.list_observations(
            ListMarketObservations(
                market_id=market_id,
                page=page,
                page_size=page_size,
                observed_from=observed_from,
                observed_to=observed_to,
            )
        )
    except MarketNotFoundError as exc:
        raise _market_not_found(exc) from exc
    return _observation_page_response(result)


@router.get(
    "/{market_id}/history",
    response_model=MarketHistoryPageResponse,
    summary="List the combined market timeline",
    operation_id="list_market_history",
)
async def list_market_history(
    market_id: UUID,
    service: Annotated[MarketQueryService, Depends(get_market_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
) -> MarketHistoryPageResponse:
    try:
        result = await service.list_history(
            ListMarketHistory(
                market_id=market_id,
                page=page,
                page_size=page_size,
            )
        )
    except MarketNotFoundError as exc:
        raise _market_not_found(exc) from exc
    return _history_page_response(result)


@router.get(
    "/{market_id}",
    response_model=MarketDetailResponse,
    summary="Get market detail",
    description=(
        "Returns one market with provider metadata and its latest snapshot. "
        "Historical snapshots remain available in storage but are not expanded "
        "by this endpoint."
    ),
    operation_id="get_market",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "The requested market does not exist.",
            "content": {"application/json": {"example": {"detail": "Market not found."}}},
        }
    },
)
async def get_market(
    market_id: UUID,
    service: Annotated[MarketQueryService, Depends(get_market_query_service)],
) -> MarketDetailResponse:
    try:
        result = await service.get(market_id)
    except MarketNotFoundError as exc:
        raise _market_not_found(exc) from exc
    return _detail_response(result)


def _provider_response(provider: ProviderSummary) -> ProviderResponse:
    return ProviderResponse(
        provider_id=provider.provider_id,
        code=provider.code,
        name=provider.name,
        enabled=provider.enabled,
    )


def _snapshot_response(snapshot: SnapshotSummary | None) -> SnapshotResponse | None:
    if snapshot is None:
        return None
    return SnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        observed_at=snapshot.observed_at,
        yes_price=snapshot.yes_price,
        no_price=snapshot.no_price,
        probability=snapshot.probability,
        spread=snapshot.spread,
        volume=snapshot.volume,
        liquidity=snapshot.liquidity,
    )


def _observation_response(
    observation: ObservationSummary | None,
) -> ObservationResponse | None:
    if observation is None:
        return None
    return ObservationResponse(
        observation_id=observation.observation_id,
        observed_at=observation.observed_at,
        probability=observation.probability,
        volume=observation.volume,
        liquidity=observation.liquidity,
        source_updated_at=observation.source_updated_at,
        ingested_at=observation.ingested_at,
        provider_code=observation.provider_code,
    )


def _summary_response(market: MarketSummary) -> MarketSummaryResponse:
    return MarketSummaryResponse(
        market_id=market.market_id,
        provider_market_id=market.provider_market_id,
        title=market.title,
        category=market.category,
        resolution_at=market.resolution_at,
        source_created_at=market.source_created_at,
        status=market.status,
        ingested_at=market.ingested_at,
        updated_at=market.updated_at,
        provider=_provider_response(market.provider),
        latest_snapshot=_snapshot_response(market.latest_snapshot),
        resolution_outcome=market.resolution_outcome,
        resolved_at=market.resolved_at,
        resolution_source=market.resolution_source,
        latest_observation=_observation_response(market.latest_observation),
        probability_change=market.probability_change,
    )


def _detail_response(market: MarketDetail) -> MarketDetailResponse:
    return MarketDetailResponse(
        **_summary_response(
            MarketSummary(
                market_id=market.market_id,
                provider_market_id=market.provider_market_id,
                title=market.title,
                category=market.category,
                resolution_at=market.resolution_at,
                source_created_at=market.source_created_at,
                status=market.status,
                ingested_at=market.ingested_at,
                updated_at=market.updated_at,
                provider=market.provider,
                latest_snapshot=market.latest_snapshot,
                resolution_outcome=market.resolution_outcome,
                resolved_at=market.resolved_at,
                resolution_source=market.resolution_source,
                latest_observation=market.latest_observation,
                probability_change=market.probability_change,
            )
        ).model_dump(),
        description=market.description,
    )


def _page_response(page: MarketPage) -> MarketPageResponse:
    return MarketPageResponse(
        items=[_summary_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )


def _observation_page_response(
    page: MarketObservationPage,
) -> ObservationPageResponse:
    return ObservationPageResponse(
        items=[cast(ObservationResponse, _observation_response(item)) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )


def _history_page_response(
    page: MarketHistoryPage,
) -> MarketHistoryPageResponse:
    return MarketHistoryPageResponse(
        items=[_history_event_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        pages=page.pages,
    )


def _history_event_response(
    event: MarketHistoryEvent,
) -> MarketHistoryEventResponse:
    return MarketHistoryEventResponse(
        event_id=event.event_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        previous_status=event.previous_status,
        status=event.status,
        resolution_outcome=event.resolution_outcome,
        probability=event.probability,
        volume=event.volume,
        liquidity=event.liquidity,
        source=event.source,
    )


def _market_not_found(exc: MarketNotFoundError) -> HTTPException:
    del exc
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Market not found.",
    )
