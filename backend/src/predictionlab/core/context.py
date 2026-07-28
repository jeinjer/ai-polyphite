from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)
trace_id_context: ContextVar[str | None] = ContextVar(
    "trace_id",
    default=None,
)


@dataclass(frozen=True, slots=True)
class ContextTokens:
    correlation_id: Token[str | None]
    trace_id: Token[str | None]


def bind_request_context(*, correlation_id: str, trace_id: str) -> ContextTokens:
    return ContextTokens(
        correlation_id=correlation_id_context.set(correlation_id),
        trace_id=trace_id_context.set(trace_id),
    )


def reset_request_context(tokens: ContextTokens) -> None:
    correlation_id_context.reset(tokens.correlation_id)
    trace_id_context.reset(tokens.trace_id)


def get_correlation_id() -> str | None:
    return correlation_id_context.get()


def get_trace_id() -> str | None:
    return trace_id_context.get()
