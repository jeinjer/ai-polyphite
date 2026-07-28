from __future__ import annotations

import asyncio

from predictionlab.runtime.collector_cli import _windows_selector_loop


def test_windows_collector_cli_uses_selector_event_loop() -> None:
    loop = _windows_selector_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()
