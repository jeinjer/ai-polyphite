"""Replay experiment orchestration over the existing collector."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from predictionlab.application.experiments import ExperimentRunStore
from predictionlab.collectors import CollectorRunResult, MarketDataCollector
from predictionlab.core.clock import ReplayClock, SystemClock
from predictionlab.domain.experiments import ExperimentRun, ExperimentRunStatus
from predictionlab.providers.replay import ReplayDatasetMetadata, ReplayModeError

type ReplayArtifactHook = Callable[
    [UUID, datetime, str],
    Awaitable[tuple[str, ...]],
]


class ReplayMode(StrEnum):
    STEP = "step"
    ACCELERATED = "accelerated"
    UNTIL = "until"


@dataclass(frozen=True, slots=True)
class ReplayExecution:
    experiment: ExperimentRun
    collector_results: tuple[CollectorRunResult, ...]
    artifact_hashes: tuple[str, ...] = ()


class ReplayRunner:
    def __init__(
        self,
        *,
        metadata: ReplayDatasetMetadata,
        replay_clock: ReplayClock,
        collector: MarketDataCollector,
        experiment_store: ExperimentRunStore,
        wall_clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        code_version: str | None = None,
    ) -> None:
        self._metadata = metadata
        self._clock = replay_clock
        self._collector = collector
        self._store = experiment_store
        self._wall_clock = wall_clock or SystemClock()
        self._id_factory = id_factory
        self._code_version = code_version

    def reset(self) -> datetime:
        return self._clock.reset()

    async def run(
        self,
        *,
        mode: ReplayMode,
        until: datetime | None = None,
        random_seed: int = 0,
        correlation_id: str | None = None,
        artifact_hook: ReplayArtifactHook | None = None,
        extension_configuration: Mapping[str, object] | None = None,
    ) -> ReplayExecution:
        _validate_mode(mode, until)
        run_id = self._id_factory()
        resolved_correlation_id = correlation_id or str(run_id)
        started_at = self._wall_clock()
        configuration_hash = _configuration_hash(
            metadata=self._metadata,
            mode=mode,
            until=until,
            random_seed=random_seed,
            extension_configuration=extension_configuration,
        )
        experiment = ExperimentRun(
            experiment_run_id=run_id,
            dataset_id=self._metadata.dataset_id,
            dataset_version=self._metadata.version,
            started_at=started_at,
            finished_at=None,
            status=ExperimentRunStatus.RUNNING,
            replay_start=self._clock.now(),
            replay_end=self._clock.now(),
            random_seed=random_seed,
            configuration_hash=configuration_hash,
            code_version=self._code_version,
            result_hash=None,
            correlation_id=resolved_correlation_id,
            safe_error_type=None,
        )
        await self._store.start(experiment)
        results: list[CollectorRunResult] = []
        artifact_hashes: list[str] = []
        try:
            await self._execute(
                experiment_run_id=run_id,
                mode=mode,
                until=until,
                correlation_id=resolved_correlation_id,
                results=results,
                artifact_hook=artifact_hook,
                artifact_hashes=artifact_hashes,
            )
            completed = experiment.complete(
                finished_at=self._wall_clock(),
                replay_end=self._clock.now(),
                result_hash=_result_hash(
                    metadata=self._metadata,
                    configuration_hash=configuration_hash,
                    replay_end=self._clock.now(),
                    artifact_hashes=tuple(artifact_hashes),
                ),
            )
            await self._store.finish(completed)
            return ReplayExecution(
                experiment=completed,
                collector_results=tuple(results),
                artifact_hashes=tuple(artifact_hashes),
            )
        except Exception as exc:
            failed = experiment.fail(
                finished_at=self._wall_clock(),
                replay_end=self._clock.now(),
                safe_error_type=type(exc).__name__,
            )
            await self._store.finish(failed)
            raise

    async def _execute(
        self,
        *,
        experiment_run_id: UUID,
        mode: ReplayMode,
        until: datetime | None,
        correlation_id: str,
        results: list[CollectorRunResult],
        artifact_hook: ReplayArtifactHook | None,
        artifact_hashes: list[str],
    ) -> None:
        if mode is ReplayMode.STEP:
            await self._collect_next(
                experiment_run_id,
                correlation_id,
                results,
                artifact_hook,
                artifact_hashes,
            )
            return

        if mode is ReplayMode.ACCELERATED:
            while self._clock.next_event_at is not None:
                await self._collect_next(
                    experiment_run_id,
                    correlation_id,
                    results,
                    artifact_hook,
                    artifact_hashes,
                )
            return

        assert until is not None
        while (
            self._clock.next_event_at is not None
            and self._clock.next_event_at <= until
        ):
            await self._collect_next(
                experiment_run_id,
                correlation_id,
                results,
                artifact_hook,
                artifact_hashes,
            )
        self._clock.advance_until(until)

    async def _collect_next(
        self,
        experiment_run_id: UUID,
        correlation_id: str,
        results: list[CollectorRunResult],
        artifact_hook: ReplayArtifactHook | None,
        artifact_hashes: list[str],
    ) -> None:
        advanced = self._clock.advance_to_next()
        if advanced is None:
            return
        results.append(
            await self._collector.collect(
                correlation_id=correlation_id,
                causation_id=f"replay:{advanced.isoformat()}",
            )
        )
        if artifact_hook is not None:
            artifact_hashes.extend(
                await artifact_hook(
                    experiment_run_id,
                    advanced,
                    correlation_id,
                )
            )


def _validate_mode(mode: ReplayMode, until: datetime | None) -> None:
    if mode is ReplayMode.UNTIL and until is None:
        raise ReplayModeError("until mode requires a timestamp.")
    if mode is not ReplayMode.UNTIL and until is not None:
        raise ReplayModeError("until timestamp is only valid with until mode.")


def _configuration_hash(
    *,
    metadata: ReplayDatasetMetadata,
    mode: ReplayMode,
    until: datetime | None,
    random_seed: int,
    extension_configuration: Mapping[str, object] | None,
) -> str:
    payload: dict[str, object] = {
        "content_sha256": metadata.content_sha256,
        "dataset_id": metadata.dataset_id,
        "dataset_version": metadata.version,
        "mode": mode.value,
        "random_seed": random_seed,
        "until": until.isoformat() if until is not None else None,
    }
    if extension_configuration is not None:
        payload["extension_configuration"] = dict(extension_configuration)
    canonical = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _result_hash(
    *,
    metadata: ReplayDatasetMetadata,
    configuration_hash: str,
    replay_end: datetime,
    artifact_hashes: tuple[str, ...] = (),
) -> str:
    payload: dict[str, object] = {
        "configuration_hash": configuration_hash,
        "content_sha256": metadata.content_sha256,
        "replay_end": replay_end.isoformat(),
    }
    if artifact_hashes:
        payload["artifact_hashes"] = artifact_hashes
    canonical = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
