"""Command-line entrypoint for one-shot and periodic collection."""

from __future__ import annotations

import argparse
import asyncio
import selectors
import signal
import sys
from collections.abc import Sequence

from predictionlab.core.logging import configure_logging
from predictionlab.core.settings import get_settings
from predictionlab.runtime.collector_runtime import create_collector_runtime


def main(arguments: Sequence[str] | None = None) -> int:
    parser = _parser()
    parsed = parser.parse_args(arguments)
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=_windows_selector_loop) as runner:
            return runner.run(_run(parsed))
    return asyncio.run(_run(parsed))


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


async def _run(arguments: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    runtime = create_collector_runtime(settings)
    loop = asyncio.get_running_loop()

    def stop() -> None:
        loop.call_soon_threadsafe(runtime.worker.stop)

    previous_sigint = signal.signal(signal.SIGINT, lambda *_: stop())
    previous_sigterm = signal.signal(signal.SIGTERM, lambda *_: stop())
    try:
        if arguments.command == "once":
            result = await runtime.worker.run_once(arguments.provider)
            return 0 if result.error_type is None else 1
        await runtime.worker.run()
        return 0
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        await runtime.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI-Polyphite market data collection runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    once = subparsers.add_parser("once", help="Run one provider cycle.")
    once.add_argument("--provider", required=True)
    subparsers.add_parser("worker", help="Run configured periodic collectors.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
