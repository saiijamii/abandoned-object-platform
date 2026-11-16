from typing import Any

from .base import Detector
from .rfdetr import RfDetrDetector
from .yolo import YoloDetector


def create_detector(config: dict[str, Any]) -> Detector:
    settings = config.get("detector", config)
    backend = settings.get("backend", "yolo").lower()
    confidence = float(settings.get("confidence", 0.15))
    device = settings.get("device", "cpu")
    if backend == "yolo":
        values = settings.get("yolo", {})
        return YoloDetector(values.get("weights", "yolov8n.pt"), confidence, int(settings.get("image_size", 640)), device)
    if backend == "rfdetr":
        values = settings.get("rfdetr", {})
        return RfDetrDetector(values.get("model", "nano"), confidence, device)
    raise ValueError(f"unsupported detector backend: {backend}")
