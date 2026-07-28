from __future__ import annotations

import logging
from uuid import UUID

from predictionlab.application.collectors.queries import (
    CollectorRunDetail,
    CollectorRunPage,
    ListCollectorRuns,
)
from predictionlab.application.collectors.repository import (
    CollectorRunReadRepository,
)

logger = logging.getLogger(__name__)


class CollectorRunNotFoundError(Exception):
    pass


class CollectorRunQueryService:
    def __init__(self, repository: CollectorRunReadRepository) -> None:
        self._repository = repository

    async def list(self, query: ListCollectorRuns) -> CollectorRunPage:
        result = await self._repository.list(query)
        logger.info(
            "collector_runs_queried",
            extra={
                "page": query.page,
                "result_count": len(result.items),
                "total": result.total,
                "provider_code": query.provider_code,
                "run_status": query.status.value if query.status else None,
            },
        )
        return result

    async def get(self, run_id: UUID) -> CollectorRunDetail:
        result = await self._repository.get(run_id)
        if result is None:
            raise CollectorRunNotFoundError(str(run_id))
        return result
