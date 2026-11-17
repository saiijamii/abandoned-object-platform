from app.metrics import percentile, timing_metrics


def test_timing_metrics() -> None:
    assert percentile([1, 2, 3, 4], .95) == 4
    assert timing_metrics([10, 20, 30]) == {"median_ms": 20, "p95_ms": 30}
