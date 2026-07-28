from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class HttpMetric:
    method: str
    route: str
    status_code: int
    request_count: int
    total_duration_ms: float
    average_duration_ms: float
    maximum_duration_ms: float


@dataclass(slots=True)
class _MutableHttpMetric:
    request_count: int = 0
    total_duration_ms: float = 0.0
    maximum_duration_ms: float = 0.0


class HttpRequestMetrics:
    """Process-local HTTP counters ready for a future metrics exporter."""

    def __init__(self) -> None:
        self._metrics: dict[tuple[str, str, int], _MutableHttpMetric] = {}
        self._lock = Lock()

    def record(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        key = (method, route, status_code)
        with self._lock:
            metric = self._metrics.setdefault(key, _MutableHttpMetric())
            metric.request_count += 1
            metric.total_duration_ms += duration_ms
            metric.maximum_duration_ms = max(
                metric.maximum_duration_ms,
                duration_ms,
            )

    def snapshot(self) -> tuple[HttpMetric, ...]:
        with self._lock:
            return tuple(
                HttpMetric(
                    method=method,
                    route=route,
                    status_code=status_code,
                    request_count=metric.request_count,
                    total_duration_ms=round(metric.total_duration_ms, 3),
                    average_duration_ms=round(
                        metric.total_duration_ms / metric.request_count,
                        3,
                    ),
                    maximum_duration_ms=round(metric.maximum_duration_ms, 3),
                )
                for (method, route, status_code), metric in sorted(self._metrics.items())
            )
