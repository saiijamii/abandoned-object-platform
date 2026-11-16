from typing import Any

from .base import Detector
from .class_map import semantic_class
from .types import Detection


class RfDetrDetector(Detector):
    """Optional adapter. RF-DETR API can vary by package version."""

    def __init__(self, model: str = "nano", confidence: float = 0.15, device: str = "cpu") -> None:
        try:
            from rfdetr import RFDETRNano, RFDETRSmall
        except ImportError as exc:
            raise RuntimeError("Install optional RF-DETR dependencies with pip install -r backend/requirements-optional.txt") from exc
        model_type = RFDETRSmall if model.lower() == "small" else RFDETRNano
        self.model = model_type()
        self.confidence = confidence
        self.device = device

    def detect(self, frame: Any) -> list[Detection]:
        result = self.model.predict(frame, threshold=self.confidence)
        detections: list[Detection] = []
        for box, score, label in zip(result.xyxy, result.confidence, result.class_id):
            semantic = semantic_class(str(label))
            if semantic is None:
                continue
            detections.append(Detection(semantic, float(score), tuple(round(float(v)) for v in box), int(label)))
        return detections
