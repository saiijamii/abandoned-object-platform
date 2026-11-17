from statistics import median
from typing import Iterable


def percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def timing_metrics(values: list[float]) -> dict[str, float]:
    return {
        "median_ms": median(values) if values else 0.0,
        "p95_ms": percentile(values, .95),
    }
