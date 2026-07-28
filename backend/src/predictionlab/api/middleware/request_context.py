from __future__ import annotations

import logging
import re
import secrets
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from predictionlab.core.context import bind_request_context, reset_request_context
from predictionlab.infrastructure.observability.http_metrics import HttpRequestMetrics

CORRELATION_ID_HEADER = "x-correlation-id"
TRACEPARENT_HEADER = "traceparent"

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TRACEPARENT_PATTERN = re.compile(
    r"^00-(?P<trace_id>[0-9a-fA-F]{32})-(?P<span_id>[0-9a-fA-F]{16})-"
    r"(?P<flags>[0-9a-fA-F]{2})$"
)
_ZERO_TRACE_ID = "0" * 32
_ZERO_SPAN_ID = "0" * 16

logger = logging.getLogger(__name__)


class RequestContextMiddleware:
    """Propagate request context and emit one structured access log."""

    def __init__(self, app: ASGIApp, *, metrics: HttpRequestMetrics) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        correlation_id = _resolve_correlation_id(headers.get(CORRELATION_ID_HEADER))
        trace_id, span_id, trace_flags = _resolve_trace_context(headers.get(TRACEPARENT_HEADER))
        response_traceparent = f"00-{trace_id}-{span_id}-{trace_flags}"
        tokens = bind_request_context(
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        started_at = perf_counter()
        status_code = 500

        async def send_with_context(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers = [
                    (key, value)
                    for key, value in response_headers
                    if key.lower()
                    not in {
                        CORRELATION_ID_HEADER.encode(),
                        TRACEPARENT_HEADER.encode(),
                    }
                ]
                response_headers.extend(
                    [
                        (CORRELATION_ID_HEADER.encode(), correlation_id.encode()),
                        (TRACEPARENT_HEADER.encode(), response_traceparent.encode()),
                    ]
                )
                message["headers"] = response_headers

            await send(message)

        try:
            await self._app(scope, receive, send_with_context)
        except Exception:
            duration_ms = _duration_ms(started_at)
            route = _route(scope)
            self._metrics.record(
                method=scope["method"],
                route=route,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            logger.exception(
                "http_request_failed",
                extra={
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "http_route": route,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            raise
        else:
            duration_ms = _duration_ms(started_at)
            route = _route(scope)
            self._metrics.record(
                method=scope["method"],
                route=route,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            logger.info(
                "http_request_completed",
                extra={
                    "http_method": scope["method"],
                    "http_path": scope["path"],
                    "http_route": route,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                },
            )
        finally:
            reset_request_context(tokens)


def _resolve_correlation_id(value: str | None) -> str:
    if value and _CORRELATION_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


def _resolve_trace_context(value: str | None) -> tuple[str, str, str]:
    if value:
        match = _TRACEPARENT_PATTERN.fullmatch(value)
        if match:
            trace_id = match.group("trace_id").lower()
            parent_span_id = match.group("span_id").lower()
            if trace_id != _ZERO_TRACE_ID and parent_span_id != _ZERO_SPAN_ID:
                return trace_id, secrets.token_hex(8), match.group("flags").lower()

    return secrets.token_hex(16), secrets.token_hex(8), "00"


def _duration_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def _route(scope: Scope) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else scope["path"]
