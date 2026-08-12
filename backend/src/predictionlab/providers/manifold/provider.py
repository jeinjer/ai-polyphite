"""Read-only adapter for Manifold Markets' official public API."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from math import isfinite
from time import monotonic
from typing import Final, Literal, cast
from urllib.parse import quote

import httpx
from pydantic import TypeAdapter, ValidationError

from predictionlab.core.hashing import canonical_sha256
from predictionlab.providers.base import (
    FetchMarketsRequest,
    FetchSnapshotsRequest,
    MarketBatch,
    MarketDataProvider,
    ProviderAuthenticationError,
    ProviderCapabilities,
    ProviderCapability,
    ProviderHealthStatus,
    ProviderMarket,
    ProviderMarketObservation,
    ProviderMarketSnapshot,
    ProviderMarketStatus,
    ProviderProtocolError,
    ProviderRateLimitError,
    ProviderResolutionOutcome,
    ProviderUnavailableError,
    SnapshotBatch,
)
from predictionlab.providers.manifold.rate_limit import (
    AsyncSleep,
    MonotonicClock,
    RequestRateLimiter,
)
from predictionlab.providers.manifold.schemas import ManifoldMarketPayload

_API_BASE_URL: Final = "https://api.manifold.markets"
_SEARCH_PATH: Final = "/v0/search-markets"
_CURSOR_PREFIX: Final = "manifold:created-time:"
_USER_AGENT: Final = "AI-Polyphite/0.1 read-only-research"
_BINARY_OUTCOME_TYPE: Final = "BINARY"
_CANCELLED_RESOLUTION: Final = "CANCEL"
_MARKET_ADAPTER = TypeAdapter(ManifoldMarketPayload)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
logger = logging.getLogger(__name__)

type Clock = Callable[[], datetime]


class ManifoldProvider(MarketDataProvider):
    """Normalize binary Manifold markets without persistence or collection logic."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        requests_per_minute: int = 450,
        clock: Clock | None = None,
        sleep: AsyncSleep | None = None,
        monotonic_clock: MonotonicClock | None = None,
        sync_mode: Literal["catalog", "recent"] = "catalog",
    ) -> None:
        super().__init__(clock=clock)
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive.")
        self._rate_limiter = RequestRateLimiter(
            requests_per_minute,
            sleep=sleep or asyncio.sleep,
            clock=monotonic_clock or monotonic,
        )
        self._timeout = httpx.Timeout(timeout_seconds)
        self._owns_client = http_client is None
        self._sync_mode = sync_mode
        self._listed_payloads: dict[str, ManifoldMarketPayload] = {}
        self._observation_signatures: dict[str, str] = {}
        self._observation_times: dict[str, datetime] = {}
        self._invalid_payloads_last_batch = 0
        self._http_client = http_client or httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=False,
        )

    @property
    def code(self) -> str:
        return "manifold"

    @property
    def name(self) -> str:
        return "Manifold Markets"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities.of(
            ProviderCapability.MARKET_LISTING,
            ProviderCapability.MARKET_DETAIL,
            ProviderCapability.LATEST_OBSERVATION,
        )

    async def fetch_markets(self, request: FetchMarketsRequest) -> MarketBatch:
        self.capabilities.require(ProviderCapability.MARKET_LISTING)
        if request.updated_after is not None:
            self.capabilities.require(ProviderCapability.INCREMENTAL_MARKETS)

        cursor_time = self._decode_cursor(request.cursor)
        params: dict[str, str | int] = {
            "sort": "last-updated" if self._sync_mode == "recent" else "newest",
            "filter": "all",
            "contractType": _BINARY_OUTCOME_TYPE,
            "limit": request.limit,
        }
        if cursor_time is not None:
            params["beforeTime"] = cursor_time

        raw = await self._get_json(_SEARCH_PATH, params=params)
        payloads = self._validate_list(raw)
        for payload in payloads:
            self._listed_payloads[payload.market_id] = payload
        now = self._now()
        markets = tuple(
            market
            for payload in payloads
            if (market := self._normalize_market(payload, now=now)) is not None
            and (not request.statuses or market.status in request.statuses)
        )
        next_cursor = (
            None
            if self._sync_mode == "recent"
            else self._next_cursor(
                payloads=payloads,
                requested_limit=request.limit,
                current_cursor=request.cursor,
            )
        )
        return MarketBatch(markets=markets, next_cursor=next_cursor)

    async def fetch_market(self, provider_market_id: str) -> ProviderMarket | None:
        self.capabilities.require(ProviderCapability.MARKET_DETAIL)
        market_id = self._validate_market_id(provider_market_id)
        raw = await self._get_json(
            f"/v0/market/{quote(market_id, safe='')}",
            allow_not_found=True,
        )
        if raw is None:
            return None
        payload = self._validate_market(raw)
        self._listed_payloads[payload.market_id] = payload
        return self._normalize_market(payload, now=self._now())

    async def fetch_latest_snapshot(
        self,
        provider_market_id: str,
    ) -> ProviderMarketSnapshot | None:
        self.capabilities.require(ProviderCapability.LATEST_SNAPSHOT)
        market_id = self._validate_market_id(provider_market_id)
        raw = await self._get_json(
            f"/v0/market/{quote(market_id, safe='')}",
            allow_not_found=True,
        )
        if raw is None:
            return None
        payload = self._validate_market(raw)
        if payload.outcome_type != _BINARY_OUTCOME_TYPE:
            return None
        return self._normalize_snapshot(payload)

    async def fetch_latest_observation(
        self,
        provider_market_id: str,
    ) -> ProviderMarketObservation | None:
        self.capabilities.require(ProviderCapability.LATEST_OBSERVATION)
        market_id = self._validate_market_id(provider_market_id)
        payload = self._listed_payloads.get(market_id)
        if payload is None:
            raw = await self._get_json(
                f"/v0/market/{quote(market_id, safe='')}",
                allow_not_found=True,
            )
            if raw is None:
                return None
            payload = self._validate_market(raw)
        if payload.outcome_type != _BINARY_OUTCOME_TYPE:
            return None
        if all(
            value is None
            for value in (
                payload.probability,
                payload.volume,
                payload.total_liquidity,
            )
        ):
            return None
        signature = canonical_sha256(
            {
                "provider_market_id": payload.market_id,
                "probability": payload.probability,
                "volume": payload.volume,
                "liquidity": payload.total_liquidity,
                "resolution": payload.resolution,
                "is_resolved": payload.is_resolved,
            }
        )
        observed_at = self._observation_times.get(payload.market_id)
        if (
            observed_at is None
            or self._observation_signatures.get(payload.market_id) != signature
        ):
            observed_at = self._now()
            self._observation_signatures[payload.market_id] = signature
            self._observation_times[payload.market_id] = observed_at
        return ProviderMarketObservation(
            provider_market_id=payload.market_id,
            observed_at=observed_at,
            probability=payload.probability,
            volume=payload.volume,
            liquidity=payload.total_liquidity,
            source_updated_at=_timestamp(payload.last_updated_time),
            raw_payload_hash=signature,
        )

    async def fetch_snapshots(
        self,
        request: FetchSnapshotsRequest,
    ) -> SnapshotBatch:
        del request
        self.capabilities.require(ProviderCapability.HISTORICAL_SNAPSHOTS)
        raise AssertionError("Provider capability validation must fail.")

    async def _probe_health(self) -> ProviderHealthStatus:
        raw = await self._get_json(
            _SEARCH_PATH,
            params={
                "sort": "last-updated" if self._sync_mode == "recent" else "newest",
                "filter": "all",
                "contractType": _BINARY_OUTCOME_TYPE,
                "limit": 300 if self._sync_mode == "recent" else 100,
            },
        )
        self._validate_list(raw)
        return (
            ProviderHealthStatus.DEGRADED
            if self._invalid_payloads_last_batch
            else ProviderHealthStatus.HEALTHY
        )

    async def aclose(self) -> None:
        """Close the internally-created HTTP client."""

        if self._owns_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> ManifoldProvider:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        del exc_type, exc, traceback
        await self.aclose()

    async def _get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        allow_not_found: bool = False,
    ) -> object | None:
        await self._rate_limiter.acquire()
        try:
            response = await self._http_client.get(
                f"{_API_BASE_URL}{path}",
                params=params,
                timeout=self._timeout,
                headers={"User-Agent": _USER_AGENT},
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError("Manifold request timed out.") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("Manifold is currently unavailable.") from exc

        if response.status_code == 404 and allow_not_found:
            return None
        self._raise_for_status(response)
        try:
            return cast(
                object,
                json.loads(response.content.decode("utf-8"), parse_float=Decimal),
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderProtocolError("Manifold returned a malformed JSON response.") from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        if status == 429:
            raise ProviderRateLimitError(
                "Manifold rate limit exceeded.",
                retry_after_seconds=self._retry_after_seconds(response.headers.get("Retry-After")),
            )
        if status in {401, 403}:
            raise ProviderAuthenticationError("Manifold rejected this public read request.")
        if status >= 500:
            raise ProviderUnavailableError("Manifold is currently unavailable.")
        raise ProviderProtocolError(f"Manifold returned unexpected HTTP status {status}.")

    def _retry_after_seconds(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value).astimezone(UTC)
            except (TypeError, ValueError, OverflowError):
                return None
            seconds = max(0.0, (retry_at - self._now()).total_seconds())
        return seconds if isfinite(seconds) and seconds >= 0 else None

    def _validate_list(self, value: object | None) -> list[ManifoldMarketPayload]:
        if not isinstance(value, list):
            raise ProviderProtocolError(
                "Manifold market-list response violated the expected schema."
            )
        payloads: list[ManifoldMarketPayload] = []
        invalid_count = 0
        for index, item in enumerate(value):
            try:
                payloads.append(_MARKET_ADAPTER.validate_python(item))
            except ValidationError as exc:
                invalid_count += 1
                logger.warning(
                    "manifold_market_payload_quarantined",
                    extra={
                        "provider_code": self.code,
                        "payload_index": index,
                        "validation_errors": tuple(
                            {
                                "location": ".".join(str(part) for part in error["loc"]),
                                "type": error["type"],
                            }
                            for error in exc.errors(include_url=False, include_input=False)
                        ),
                    },
                )
        self._invalid_payloads_last_batch = invalid_count
        if value and not payloads:
            raise ProviderProtocolError(
                "Every Manifold market payload violated the expected schema."
            )
        if invalid_count:
            logger.warning(
                "manifold_market_batch_degraded",
                extra={
                    "provider_code": self.code,
                    "received_count": len(value),
                    "accepted_count": len(payloads),
                    "quarantined_count": invalid_count,
                },
            )
        return payloads

    @staticmethod
    def _validate_market(value: object) -> ManifoldMarketPayload:
        try:
            return _MARKET_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise ProviderProtocolError(
                "Manifold market response violated the expected schema."
            ) from exc

    def _normalize_market(
        self,
        payload: ManifoldMarketPayload,
        *,
        now: datetime,
    ) -> ProviderMarket | None:
        if payload.outcome_type != _BINARY_OUTCOME_TYPE:
            return None
        category = next(
            (value.strip() for value in payload.group_slugs if value.strip()),
            None,
        )
        return ProviderMarket(
            provider_market_id=payload.market_id,
            title=payload.question,
            description=payload.text_description,
            category=category,
            status=self._market_status(payload, now=now),
            resolution_at=_timestamp(payload.close_time),
            source_created_at=_timestamp(payload.created_time),
            source_updated_at=_timestamp(payload.last_updated_time),
            resolution_outcome=self._resolution_outcome(payload),
            resolved_at=(_timestamp(payload.resolution_time) if payload.is_resolved else None),
            resolution_source=("manifold_public_api" if payload.is_resolved else None),
        )

    def _normalize_snapshot(
        self,
        payload: ManifoldMarketPayload,
    ) -> ProviderMarketSnapshot | None:
        if payload.probability is None:
            return None
        return ProviderMarketSnapshot(
            provider_market_id=payload.market_id,
            observed_at=(
                _timestamp(payload.last_updated_time)
                or _timestamp(payload.resolution_time)
                or self._now()
            ),
            yes_price=None,
            no_price=None,
            probability=payload.probability,
            spread=None,
            volume=payload.volume,
            liquidity=payload.total_liquidity,
        )

    @staticmethod
    def _market_status(
        payload: ManifoldMarketPayload,
        *,
        now: datetime,
    ) -> ProviderMarketStatus:
        if payload.is_resolved and payload.resolution == _CANCELLED_RESOLUTION:
            return ProviderMarketStatus.CANCELLED
        if payload.is_resolved:
            return ProviderMarketStatus.RESOLVED
        close_time = _timestamp(payload.close_time)
        if close_time is not None and close_time <= now:
            return ProviderMarketStatus.CLOSED
        return ProviderMarketStatus.OPEN

    @staticmethod
    def _resolution_outcome(
        payload: ManifoldMarketPayload,
    ) -> ProviderResolutionOutcome:
        if not payload.is_resolved:
            return ProviderResolutionOutcome.UNRESOLVED
        if payload.resolution == "YES":
            return ProviderResolutionOutcome.YES
        if payload.resolution == "NO":
            return ProviderResolutionOutcome.NO
        if payload.resolution == _CANCELLED_RESOLUTION:
            return ProviderResolutionOutcome.CANCELLED
        return ProviderResolutionOutcome.OTHER

    @staticmethod
    def _validate_market_id(value: str) -> str:
        stripped = value.strip()
        if not stripped or len(stripped) > 512:
            raise ProviderProtocolError("Invalid Manifold market identifier.")
        return stripped

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int | None:
        if cursor is None:
            return None
        if not cursor.startswith(_CURSOR_PREFIX):
            raise ProviderProtocolError("Invalid Manifold cursor.")
        try:
            value = int(cursor.removeprefix(_CURSOR_PREFIX))
        except ValueError as exc:
            raise ProviderProtocolError("Invalid Manifold cursor.") from exc
        if value < 0:
            raise ProviderProtocolError("Invalid Manifold cursor.")
        return value

    @staticmethod
    def _next_cursor(
        *,
        payloads: list[ManifoldMarketPayload],
        requested_limit: int,
        current_cursor: str | None,
    ) -> str | None:
        if len(payloads) < requested_limit or not payloads:
            return None
        cursor = f"{_CURSOR_PREFIX}{payloads[-1].created_time}"
        if cursor == current_cursor:
            raise ProviderProtocolError("Manifold returned a non-advancing cursor.")
        return cursor

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Provider clock must return a timezone-aware datetime.")
        return value.astimezone(UTC)


def _timestamp(milliseconds: int | None) -> datetime | None:
    if milliseconds is None:
        return None
    try:
        return _EPOCH + timedelta(milliseconds=milliseconds)
    except OverflowError as exc:
        raise ProviderProtocolError("Manifold returned an invalid timestamp.") from exc
