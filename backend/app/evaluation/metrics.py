from collections import defaultdict
from collections import Counter
from typing import Iterable

from ..detection.types import Detection


def iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    x1, y1 = max(left[0], right[0]), max(left[1], right[1])
    x2, y2 = min(left[2], right[2]), min(left[3], right[3])
    overlap = max(0, x2 - x1) * max(0, y2 - y1)
    area_left = max(0, left[2] - left[0]) * max(0, left[3] - left[1])
    area_right = max(0, right[2] - right[0]) * max(0, right[3] - right[1])
    union = area_left + area_right - overlap
    return overlap / union if union else 0.0


def score_frame(predictions: Iterable[Detection], truth: Iterable[Detection], threshold: float = 0.5) -> Counter:
    predictions, truth = list(predictions), list(truth)
    matched: set[int] = set()
    counts = Counter()
    for prediction in predictions:
        candidates = [(index, expected) for index, expected in enumerate(truth) if index not in matched and expected.class_name == prediction.class_name]
        match = max(candidates, key=lambda item: iou(prediction.bbox, item[1].bbox), default=None)
        if match and iou(prediction.bbox, match[1].bbox) >= threshold:
            matched.add(match[0])
            counts[(prediction.class_name, "tp")] += 1
        else:
            counts[(prediction.class_name, "fp")] += 1
    for index, expected in enumerate(truth):
        if index not in matched:
            counts[(expected.class_name, "fn")] += 1
    return counts


def precision_recall(true_positive: int | Counter, false_positive: int | str, false_negative: int | None = None) -> dict[str, float]:
    if isinstance(true_positive, Counter):
        counts, class_name = true_positive, str(false_positive)
        true_positive = counts[(class_name, "tp")]
        false_positive = counts[(class_name, "fp")]
        false_negative = counts[(class_name, "fn")]
    assert false_negative is not None
    return {
        "precision": true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0,
        "recall": true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0,
    }


def summarize_slices(rows: list[dict]) -> dict[str, dict[str, float]]:
    counts = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        for tag in str(row.get("tags", "")).split(";"):
            if tag:
                counts[tag][0] += int(row.get("true_positive", 0))
                counts[tag][1] += int(row.get("false_positive", 0))
                counts[tag][2] += int(row.get("false_negative", 0))
    return {tag: precision_recall(*values) for tag, values in counts.items()}
