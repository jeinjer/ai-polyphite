"""CLI for one-shot and periodic continuous paper validation."""

from __future__ import annotations

import argparse
import asyncio
import selectors
import signal
import sys
from collections.abc import Sequence
from datetime import datetime

from predictionlab.application.paper_validation import (
    PaperValidationRunFailedError,
)
from predictionlab.core.logging import configure_logging
from predictionlab.core.settings import get_settings
from predictionlab.runtime.paper_validation_runtime import (
    create_paper_validation_runtime,
)


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
    runtime = create_paper_validation_runtime(settings)
    loop = asyncio.get_running_loop()

    def stop() -> None:
        loop.call_soon_threadsafe(runtime.worker.stop)

    previous_sigint = signal.signal(signal.SIGINT, lambda *_: stop())
    previous_sigterm = signal.signal(signal.SIGTERM, lambda *_: stop())
    try:
        if arguments.command == "once":
            try:
                result = await runtime.worker.run_once(
                    scheduled_for=_parse_datetime(arguments.scheduled_for),
                )
            except PaperValidationRunFailedError:
                return 1
            return 0 if result.safe_error_type is None else 1
        await runtime.worker.run()
        return 0
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        await runtime.close()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("--scheduled-for must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--scheduled-for must include a timezone")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI-Polyphite continuous simulated validation runtime."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    once = subparsers.add_parser("once", help="Run one idempotent validation cycle.")
    once.add_argument(
        "--scheduled-for",
        help="Optional ISO-8601 logical cycle timestamp; defaults to current slot.",
    )
    subparsers.add_parser("worker", help="Run validation on the configured cadence.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
