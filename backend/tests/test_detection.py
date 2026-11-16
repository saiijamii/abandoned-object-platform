from collections import Counter

import pytest

from app.detection.class_map import semantic_class
from app.detection.types import Detection
from app.evaluation import iou, precision_recall, score_frame


def test_semantic_mapping() -> None:
    assert semantic_class("person") == "person"
    assert semantic_class("suitcase") == "luggage"
    assert semantic_class("bench") is None


def test_detection_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError):
        Detection("person", 1.1, (0, 0, 1, 1))


def test_scoring_and_iou() -> None:
    expected = [Detection("luggage", 1, (0, 0, 10, 10))]
    actual = [Detection("luggage", 0.9, (1, 1, 9, 9))]
    counts = score_frame(actual, expected)
    assert iou(actual[0].bbox, expected[0].bbox) > 0.5
    assert precision_recall(counts, "luggage") == {"precision": 1.0, "recall": 1.0}
