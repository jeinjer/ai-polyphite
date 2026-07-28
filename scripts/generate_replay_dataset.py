"""Generate the versioned synthetic replay fixture used by tests and demos."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend" / "datasets" / "replay" / "synthetic-lab-v1.jsonl"
BASE = datetime(2026, 1, 1, tzinfo=UTC)
CATEGORIES = ("tecnologia", "ciencia", "energia", "clima", "sociedad")


def main() -> None:
    records: list[dict[str, Any]] = []
    for index in range(1, 21):
        market_id = f"synthetic-{index:02d}"
        available_at = BASE + timedelta(hours=(index - 1) * 2)
        close_at = available_at + timedelta(days=5)
        resolution_at = available_at + timedelta(days=6)
        records.append(
            {
                "type": "market",
                "provider_market_id": market_id,
                "available_at": _time(available_at),
                "title": f"¿Se cumplirá el evento sintético {index:02d}?",
                "description": "Mercado ficticio generado para experimentos reproducibles.",
                "category": CATEGORIES[(index - 1) % len(CATEGORIES)],
                "resolution_at": _time(close_at),
                "initial_status": "open",
            }
        )

        base_probability = 25 + (index * 7) % 50
        for observation_index in range(1, 5):
            observed_at = available_at + timedelta(days=observation_index)
            direction = 1 if index % 2 == 0 else -1
            probability = max(
                5,
                min(95, base_probability + direction * observation_index * 4),
            )
            records.append(
                {
                    "type": "observation",
                    "provider_market_id": market_id,
                    "observed_at": _time(observed_at),
                    "probability": f"{probability / 100:.2f}",
                    "volume": f"{100 + index * 11 + observation_index * 13:.2f}",
                    "liquidity": (
                        None
                        if observation_index == 1 and index % 3 == 0
                        else f"{50 + index * 3 + observation_index * 5:.2f}"
                    ),
                    "source_updated_at": _time(observed_at),
                }
            )

        records.append(
            {
                "type": "state_change",
                "provider_market_id": market_id,
                "occurred_at": _time(close_at),
                "status": "closed",
            }
        )
        outcome = "cancelled" if index % 5 == 0 else ("yes" if index % 2 == 0 else "no")
        records.append(
            {
                "type": "resolution",
                "provider_market_id": market_id,
                "occurred_at": _time(resolution_at),
                "outcome": outcome,
                "source": "synthetic_fixture_v1",
            }
        )

    records.sort(
        key=lambda item: (
            item.get("available_at")
            or item.get("observed_at")
            or item.get("occurred_at"),
            item["type"],
            item["provider_market_id"],
        )
    )
    event_lines = [_json(record) for record in records]
    content = ("\n".join(event_lines) + "\n").encode()
    metadata = {
        "type": "metadata",
        "dataset_id": "synthetic-lab",
        "version": "1.0.0",
        "schema_version": "1",
        "created_at": _time(BASE),
        "description": (
            "Veinte mercados binarios completamente sintéticos para validar replay, "
            "resoluciones y ausencia de lookahead."
        ),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "replay_start": (
            records[0].get("available_at")
            or records[0].get("observed_at")
            or records[0]["occurred_at"]
        ),
        "replay_end": (
            records[-1].get("available_at")
            or records[-1].get("observed_at")
            or records[-1]["occurred_at"]
        ),
        "market_count": 20,
        "observation_count": 80,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        f"{_json(metadata)}\n" + content.decode(),
        encoding="utf-8",
        newline="\n",
    )


def _time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


if __name__ == "__main__":
    main()
