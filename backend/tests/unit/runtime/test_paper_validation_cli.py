from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from predictionlab.runtime.paper_validation_cli import (
    _parse_datetime,
    _windows_selector_loop,
)


def test_windows_paper_validation_cli_uses_selector_event_loop() -> None:
    loop = _windows_selector_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_cli_timestamp_requires_timezone() -> None:
    assert _parse_datetime("2026-07-28T12:00:00Z") == datetime(
        2026,
        7,
        28,
        12,
        tzinfo=UTC,
    )
    with pytest.raises(ValueError, match="timezone"):
        _parse_datetime("2026-07-28T12:00:00")
