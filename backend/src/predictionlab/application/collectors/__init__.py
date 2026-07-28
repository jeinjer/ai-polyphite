"""Read-only collector run queries."""

from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)
from predictionlab.application.collectors.service import CollectorRunQueryService

__all__ = [
    "CollectorRunDetail",
    "CollectorRunPage",
    "CollectorRunQueryService",
    "ListCollectorRuns",
]
