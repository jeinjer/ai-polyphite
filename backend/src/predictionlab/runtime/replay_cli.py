"""CLI for deterministic historical replay."""

from __future__ import annotations

import argparse
import asyncio
import selectors
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from predictionlab.core.logging import configure_logging
from predictionlab.core.settings import Settings, get_settings
from predictionlab.providers.replay import discover_replay_datasets
from predictionlab.runtime.replay_runner import ReplayMode
from predictionlab.runtime.replay_runtime import create_replay_runtime


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = _parser().parse_args(arguments)
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=_windows_selector_loop) as runner:
            return runner.run(_run(parsed))
    return asyncio.run(_run(parsed))


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


async def _run(arguments: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    dataset_path = resolve_dataset_path(arguments.dataset, settings)
    runtime = create_replay_runtime(settings, dataset_path)
    try:
        if arguments.command == "reset":
            reset_at = runtime.runner.reset()
            print(f"Replay clock reset to {reset_at.isoformat()}.")
            return 0
        execution = await runtime.runner.run(
            mode=ReplayMode(arguments.mode),
            until=_parse_timestamp(arguments.until),
            random_seed=arguments.seed,
        )
        print(
            "Experiment "
            f"{execution.experiment.experiment_run_id} "
            f"{execution.experiment.status.value}; "
            f"result_hash={execution.experiment.result_hash}."
        )
        return 0 if execution.experiment.safe_error_type is None else 1
    finally:
        await runtime.close()


def resolve_dataset_path(value: str, settings: Settings) -> Path:
    direct = Path(value)
    if direct.is_file():
        return direct
    named = settings.replay_dataset_directory / (
        value if value.endswith(".jsonl") else f"{value}.jsonl"
    )
    if named.is_file():
        return named
    for dataset in discover_replay_datasets(settings.replay_dataset_directory):
        if dataset.metadata.dataset_id == value:
            return dataset.path
    raise FileNotFoundError(f"Replay dataset '{value}' was not found.")


def _parse_timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI-Polyphite replay runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Execute a historical experiment.")
    run.add_argument("--dataset", required=True)
    run.add_argument(
        "--mode",
        choices=[mode.value for mode in ReplayMode],
        default=ReplayMode.ACCELERATED.value,
    )
    run.add_argument("--until")
    run.add_argument("--seed", type=int, default=0)
    reset = subparsers.add_parser("reset", help="Validate a dataset and reset its clock.")
    reset.add_argument("--dataset", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
