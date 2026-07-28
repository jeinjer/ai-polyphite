"""Versioned JSONL dataset loading and integrity validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from predictionlab.providers.base import ProviderMarketStatus, ProviderResolutionOutcome
from predictionlab.providers.replay.errors import (
    ReplayDatasetFormatError,
    ReplayDatasetIntegrityError,
)

DatasetId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$"),
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include timezone information")
    return value.astimezone(UTC)


class ReplayRecord(BaseModel):
    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class ReplayDatasetMetadata(ReplayRecord):
    type: Literal["metadata"]
    dataset_id: DatasetId
    version: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    schema_version: Literal["1"]
    created_at: datetime
    description: Annotated[str, StringConstraints(min_length=1, max_length=2_000)]
    content_sha256: Sha256
    replay_start: datetime
    replay_end: datetime
    market_count: int = Field(ge=1)
    observation_count: int = Field(ge=1)

    _normalize_times = field_validator(
        "created_at",
        "replay_start",
        "replay_end",
        mode="after",
    )(_utc)


class ReplayMarketRecord(ReplayRecord):
    type: Literal["market"]
    provider_market_id: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    available_at: datetime
    title: Annotated[str, StringConstraints(min_length=1, max_length=1_000)]
    description: Annotated[str, StringConstraints(max_length=20_000)] | None = None
    category: Annotated[str, StringConstraints(max_length=200)] | None = None
    resolution_at: datetime | None = None
    initial_status: Literal[ProviderMarketStatus.OPEN] = ProviderMarketStatus.OPEN

    _normalize_times = field_validator(
        "available_at",
        "resolution_at",
        mode="after",
    )(_utc)


class ReplayObservationRecord(ReplayRecord):
    type: Literal["observation"]
    provider_market_id: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    observed_at: datetime
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    volume: Decimal | None = Field(default=None, ge=0)
    liquidity: Decimal | None = Field(default=None, ge=0)
    source_updated_at: datetime | None = None
    raw_payload_hash: Sha256 | None = None

    _normalize_times = field_validator(
        "observed_at",
        "source_updated_at",
        mode="after",
    )(_utc)


class ReplayStateChangeRecord(ReplayRecord):
    type: Literal["state_change"]
    provider_market_id: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    occurred_at: datetime
    status: Literal[ProviderMarketStatus.OPEN, ProviderMarketStatus.CLOSED]

    _normalize_occurred_at = field_validator("occurred_at", mode="after")(_utc)


class ReplayResolutionRecord(ReplayRecord):
    type: Literal["resolution"]
    provider_market_id: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    occurred_at: datetime
    outcome: Literal[
        ProviderResolutionOutcome.YES,
        ProviderResolutionOutcome.NO,
        ProviderResolutionOutcome.CANCELLED,
    ]
    source: Annotated[str, StringConstraints(min_length=1, max_length=200)]

    _normalize_occurred_at = field_validator("occurred_at", mode="after")(_utc)


type ReplayEventRecord = (
    ReplayMarketRecord
    | ReplayObservationRecord
    | ReplayStateChangeRecord
    | ReplayResolutionRecord
)

_RECORD_TYPES: dict[str, type[ReplayEventRecord]] = {
    "market": ReplayMarketRecord,
    "observation": ReplayObservationRecord,
    "state_change": ReplayStateChangeRecord,
    "resolution": ReplayResolutionRecord,
}


@dataclass(frozen=True, slots=True)
class ReplayDataset:
    metadata: ReplayDatasetMetadata
    markets: tuple[ReplayMarketRecord, ...]
    observations: tuple[ReplayObservationRecord, ...]
    state_changes: tuple[ReplayStateChangeRecord, ...]
    resolutions: tuple[ReplayResolutionRecord, ...]
    event_times: tuple[datetime, ...]
    path: Path


def load_replay_dataset(path: Path) -> ReplayDataset:
    """Read, hash and semantically validate one UTF-8 JSONL dataset."""

    resolved_path = path.resolve()
    try:
        raw = resolved_path.read_bytes()
    except OSError as exc:
        raise ReplayDatasetFormatError("Replay dataset could not be read.") from exc

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReplayDatasetFormatError("Replay dataset must use UTF-8.") from exc

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ReplayDatasetFormatError("Replay dataset requires metadata and event records.")

    metadata_payload = _json(lines[0], line_number=1)
    try:
        metadata = ReplayDatasetMetadata.model_validate(metadata_payload)
    except ValidationError as exc:
        raise ReplayDatasetFormatError("Replay dataset metadata is invalid.") from exc

    content_bytes = ("\n".join(lines[1:]) + "\n").encode()
    actual_hash = hashlib.sha256(content_bytes).hexdigest()
    if actual_hash != metadata.content_sha256:
        raise ReplayDatasetIntegrityError("Replay dataset SHA-256 does not match its content.")

    records = tuple(
        _event_record(_json(line, line_number=index), line_number=index)
        for index, line in enumerate(lines[1:], start=2)
    )
    dataset = ReplayDataset(
        metadata=metadata,
        markets=tuple(record for record in records if isinstance(record, ReplayMarketRecord)),
        observations=tuple(
            record for record in records if isinstance(record, ReplayObservationRecord)
        ),
        state_changes=tuple(
            record for record in records if isinstance(record, ReplayStateChangeRecord)
        ),
        resolutions=tuple(
            record for record in records if isinstance(record, ReplayResolutionRecord)
        ),
        event_times=tuple(sorted({_event_time(record) for record in records})),
        path=resolved_path,
    )
    _validate_dataset(dataset)
    return dataset


def discover_replay_datasets(directory: Path) -> tuple[ReplayDataset, ...]:
    if not directory.exists():
        return ()
    return tuple(load_replay_dataset(path) for path in sorted(directory.glob("*.jsonl")))


def _json(line: str, *, line_number: int) -> object:
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ReplayDatasetFormatError(
            f"Replay dataset line {line_number} is not valid JSON."
        ) from exc


def _event_record(payload: object, *, line_number: int) -> ReplayEventRecord:
    if not isinstance(payload, dict):
        raise ReplayDatasetFormatError(f"Replay dataset line {line_number} must be an object.")
    record_type = payload.get("type")
    model = _RECORD_TYPES.get(record_type) if isinstance(record_type, str) else None
    if model is None:
        raise ReplayDatasetFormatError(
            f"Replay dataset line {line_number} has an unsupported record type."
        )
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ReplayDatasetFormatError(
            f"Replay dataset line {line_number} is invalid."
        ) from exc


def _validate_dataset(dataset: ReplayDataset) -> None:
    metadata = dataset.metadata
    if metadata.replay_end < metadata.replay_start:
        raise ReplayDatasetFormatError("replay_end cannot precede replay_start.")
    if not dataset.markets:
        raise ReplayDatasetFormatError("Replay dataset must contain markets.")
    market_ids = [record.provider_market_id for record in dataset.markets]
    if len(set(market_ids)) != len(market_ids):
        raise ReplayDatasetFormatError("Replay market identifiers must be unique.")
    known_markets = set(market_ids)

    if metadata.market_count != len(dataset.markets):
        raise ReplayDatasetFormatError("Declared market_count does not match the dataset.")
    if metadata.observation_count != len(dataset.observations):
        raise ReplayDatasetFormatError("Declared observation_count does not match the dataset.")
    if dataset.event_times[0] != metadata.replay_start:
        raise ReplayDatasetFormatError("Declared replay_start does not match the first event.")
    if dataset.event_times[-1] != metadata.replay_end:
        raise ReplayDatasetFormatError("Declared replay_end does not match the last event.")

    created_at = {
        record.provider_market_id: record.available_at for record in dataset.markets
    }
    referenced_events: tuple[
        ReplayObservationRecord | ReplayStateChangeRecord | ReplayResolutionRecord,
        ...,
    ] = (*dataset.observations, *dataset.state_changes, *dataset.resolutions)
    for record in referenced_events:
        if record.provider_market_id not in known_markets:
            raise ReplayDatasetFormatError("Replay event references an unknown market.")
        event_time = _event_time(record)
        if event_time < created_at[record.provider_market_id]:
            raise ReplayDatasetFormatError("Replay event predates its market.")
        if not metadata.replay_start <= event_time <= metadata.replay_end:
            raise ReplayDatasetFormatError("Replay event falls outside the declared range.")

    observation_keys = [
        (record.provider_market_id, record.observed_at) for record in dataset.observations
    ]
    if len(set(observation_keys)) != len(observation_keys):
        raise ReplayDatasetFormatError("Replay observations must have unique market timestamps.")
    if any(
        all(
            value is None
            for value in (record.probability, record.volume, record.liquidity)
        )
        for record in dataset.observations
    ):
        raise ReplayDatasetFormatError("Replay observations must contain at least one value.")

    resolution_markets = [record.provider_market_id for record in dataset.resolutions]
    if len(set(resolution_markets)) != len(resolution_markets):
        raise ReplayDatasetFormatError("A replay market can have only one final resolution.")


def _event_time(record: ReplayEventRecord) -> datetime:
    if isinstance(record, ReplayMarketRecord):
        return record.available_at
    if isinstance(record, ReplayObservationRecord):
        return record.observed_at
    return record.occurred_at
