from predictionlab.infrastructure.observability.http_metrics import (
    HttpRequestMetrics,
)


def test_http_metrics_aggregate_by_method_route_and_status() -> None:
    metrics = HttpRequestMetrics()

    metrics.record(
        method="GET",
        route="/markets/{market_id}",
        status_code=200,
        duration_ms=10.0,
    )
    metrics.record(
        method="GET",
        route="/markets/{market_id}",
        status_code=200,
        duration_ms=20.0,
    )
    metrics.record(
        method="GET",
        route="/markets/{market_id}",
        status_code=404,
        duration_ms=5.0,
    )

    successful, missing = metrics.snapshot()
    assert successful.request_count == 2
    assert successful.total_duration_ms == 30.0
    assert successful.average_duration_ms == 15.0
    assert successful.maximum_duration_ms == 20.0
    assert missing.request_count == 1
    assert missing.status_code == 404
