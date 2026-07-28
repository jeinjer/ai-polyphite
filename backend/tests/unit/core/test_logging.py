from __future__ import annotations

import json
import logging

from predictionlab.core.context import bind_request_context, reset_request_context
from predictionlab.core.logging import JsonFormatter


def test_json_formatter_includes_execution_context_and_extra_fields() -> None:
    formatter = JsonFormatter(
        service_name="predictionlab-test",
        environment="testing",
    )
    record = logging.LogRecord(
        name="predictionlab.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="test_event",
        args=(),
        exc_info=None,
    )
    record.component = "postgres"
    tokens = bind_request_context(
        correlation_id="correlation-123",
        trace_id="a" * 32,
    )

    try:
        payload = json.loads(formatter.format(record))
    finally:
        reset_request_context(tokens)

    assert payload["message"] == "test_event"
    assert payload["service"] == "predictionlab-test"
    assert payload["environment"] == "testing"
    assert payload["correlation_id"] == "correlation-123"
    assert payload["trace_id"] == "a" * 32
    assert payload["component"] == "postgres"
    assert payload["timestamp"].endswith("Z")
