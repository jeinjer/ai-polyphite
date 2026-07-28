from __future__ import annotations

import hashlib
import json
from datetime import UTC, timedelta
from pathlib import Path

import pytest

from predictionlab.core.clock import ReplayClock
from predictionlab.providers.base import FetchMarketsRequest, ProviderMarketStatus
from predictionlab.providers.replay import (
    ReplayDatasetFormatError,
    ReplayDatasetIntegrityError,
    ReplayProvider,
    load_replay_dataset,
)

DATASET = Path(__file__).parents[3] / "datasets" / "replay" / "synthetic-lab-v1.jsonl"


def test_dataset_manifest_and_utc_integrity() -> None:
    dataset = load_replay_dataset(DATASET)

    assert dataset.metadata.dataset_id == "synthetic-lab"
    assert len(dataset.markets) == 20
    assert len(dataset.observations) == 80
    assert all(value.tzinfo is UTC for value in dataset.event_times)
    assert {resolution.outcome.value for resolution in dataset.resolutions} == {
        "yes",
        "no",
        "cancelled",
    }


def test_dataset_rejects_an_incorrect_hash(tmp_path: Path) -> None:
    lines = DATASET.read_text(encoding="utf-8").splitlines()
    lines[-1] = lines[-1].replace("synthetic_fixture_v1", "tampered")
    invalid = tmp_path / "invalid-hash.jsonl"
    invalid.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ReplayDatasetIntegrityError):
        load_replay_dataset(invalid)


def test_dataset_rejects_naive_timestamps_even_with_valid_hash(tmp_path: Path) -> None:
    lines = DATASET.read_text(encoding="utf-8").splitlines()
    metadata = json.loads(lines[0])
    first_event = json.loads(lines[1])
    first_event["available_at"] = first_event["available_at"].removesuffix("Z")
    lines[1] = json.dumps(first_event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    content = ("\n".join(lines[1:]) + "\n").encode()
    metadata["content_sha256"] = hashlib.sha256(content).hexdigest()
    lines[0] = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    invalid = tmp_path / "naive-time.jsonl"
    invalid.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ReplayDatasetFormatError):
        load_replay_dataset(invalid)


@pytest.mark.asyncio
async def test_provider_blocks_future_observations_and_resolutions() -> None:
    dataset = load_replay_dataset(DATASET)
    clock = ReplayClock(
        start_at=dataset.metadata.replay_start,
        event_times=dataset.event_times,
    )
    provider = ReplayProvider(DATASET, clock=clock)

    start_batch = await provider.fetch_markets(FetchMarketsRequest(limit=100))
    first_market = start_batch.markets[0]
    assert first_market.provider_market_id == "synthetic-01"
    assert first_market.status is ProviderMarketStatus.OPEN
    assert first_market.resolution_outcome.value == "unresolved"
    assert await provider.fetch_latest_observation("synthetic-01") is None

    clock.advance_until(dataset.metadata.replay_start + timedelta(days=4))
    visible_observation = await provider.fetch_latest_observation("synthetic-01")
    before_resolution = await provider.fetch_market("synthetic-01")
    assert visible_observation is not None
    assert visible_observation.observed_at <= clock.now()
    assert before_resolution is not None
    assert before_resolution.resolution_outcome.value == "unresolved"

    resolution_time = next(
        item.occurred_at
        for item in dataset.resolutions
        if item.provider_market_id == "synthetic-01"
    )
    clock.advance_until(resolution_time)
    resolved = await provider.fetch_market("synthetic-01")
    assert resolved is not None
    assert resolved.status is ProviderMarketStatus.RESOLVED
    assert resolved.resolved_at == resolution_time


@pytest.mark.asyncio
async def test_provider_pagination_is_stable_at_simulated_time() -> None:
    dataset = load_replay_dataset(DATASET)
    clock = ReplayClock(
        start_at=dataset.metadata.replay_start,
        event_times=dataset.event_times,
    )
    clock.advance_until(dataset.metadata.replay_end)
    provider = ReplayProvider(DATASET, clock=clock)

    first = await provider.fetch_markets(FetchMarketsRequest(limit=7))
    second = await provider.fetch_markets(
        FetchMarketsRequest(cursor=first.next_cursor, limit=7)
    )
    third = await provider.fetch_markets(
        FetchMarketsRequest(cursor=second.next_cursor, limit=7)
    )

    identifiers = {
        market.provider_market_id
        for batch in (first, second, third)
        for market in batch.markets
    }
    assert len(identifiers) == 20
    assert third.next_cursor is None
