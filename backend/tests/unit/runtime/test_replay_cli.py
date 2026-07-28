from __future__ import annotations

from pathlib import Path

from predictionlab.core.settings import Settings
from predictionlab.runtime import replay_cli


def test_replay_cli_parses_required_modes() -> None:
    parser = replay_cli._parser()

    accelerated = parser.parse_args(
        ["run", "--dataset", "synthetic-lab-v1", "--mode", "accelerated"]
    )
    step = parser.parse_args(["run", "--dataset", "synthetic-lab-v1", "--mode", "step"])
    reset = parser.parse_args(["reset", "--dataset", "synthetic-lab-v1"])

    assert accelerated.mode == "accelerated"
    assert step.mode == "step"
    assert reset.command == "reset"


def test_replay_cli_resolves_a_versioned_dataset() -> None:
    backend_root = Path(__file__).parents[3]
    settings = Settings(
        _env_file=None,
        replay_dataset_directory=backend_root / "datasets" / "replay",
    )

    resolved = replay_cli.resolve_dataset_path("synthetic-lab-v1", settings)

    assert resolved.name == "synthetic-lab-v1.jsonl"
