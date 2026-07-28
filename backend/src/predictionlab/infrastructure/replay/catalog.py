"""Read-only discovery of safe replay dataset manifests."""

from __future__ import annotations

from pathlib import Path

from predictionlab.application.experiments import ReplayDatasetSummary
from predictionlab.providers.replay import discover_replay_datasets


class FileReplayDatasetCatalog:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def list(self) -> tuple[ReplayDatasetSummary, ...]:
        return tuple(
            ReplayDatasetSummary(
                dataset_id=dataset.metadata.dataset_id,
                version=dataset.metadata.version,
                schema_version=dataset.metadata.schema_version,
                created_at=dataset.metadata.created_at,
                description=dataset.metadata.description,
                content_sha256=dataset.metadata.content_sha256,
                replay_start=dataset.metadata.replay_start,
                replay_end=dataset.metadata.replay_end,
                market_count=dataset.metadata.market_count,
                observation_count=dataset.metadata.observation_count,
            )
            for dataset in discover_replay_datasets(self._directory)
        )
