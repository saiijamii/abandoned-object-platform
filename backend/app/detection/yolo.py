from typing import Any

from .base import Detector
from .class_map import semantic_class
from .types import Detection


class YoloDetector(Detector):
    def __init__(self, weights: str, confidence: float = 0.15, image_size: int = 640, device: str = "cpu") -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install optional YOLO dependencies with pip install -r backend/requirements-optional.txt") from exc
        self.model = YOLO(weights)
        self.confidence = confidence
        self.image_size = image_size
        self.device = device

    def detect(self, frame: Any) -> list[Detection]:
        result = self.model.predict(frame, conf=self.confidence, imgsz=self.image_size, device=self.device, verbose=False)[0]
        names = result.names
        detections: list[Detection] = []
        for box in result.boxes:
            source_id = int(box.cls.item())
            semantic = semantic_class(str(names[source_id]))
            if semantic is None:
                continue
            xyxy = [round(float(value)) for value in box.xyxy[0].tolist()]
            detections.append(Detection(semantic, float(box.conf.item()), tuple(xyxy), source_id))
        return detections
