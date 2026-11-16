import json
import time
from pathlib import Path
from typing import Any

import cv2

from .detection.base import Detector


def draw_detections(frame: Any, detections: list) -> Any:
    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (23, 23, 23), 2)
        cv2.putText(frame, f"{detection.class_name} {detection.confidence:.2f}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, .55, (23, 23, 23), 2)
    return frame


def process_video(input_path: str | Path, output_path: str | Path, detector: Detector, manifest_path: str | Path | None = None) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video: {input_path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise ValueError(f"cannot open output video: {output_path}")
    frames = 0
    timings: list[float] = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            started = time.perf_counter()
            detections = detector.detect(frame)
            timings.append((time.perf_counter() - started) * 1000)
            writer.write(draw_detections(frame, detections))
            frames += 1
    finally:
        capture.release()
        writer.release()
    result = {"input": str(input_path), "output": str(output), "frames": frames, "source_fps": fps, "median_inference_ms": sorted(timings)[len(timings) // 2] if timings else 0.0}
    if manifest_path:
        manifest = Path(manifest_path)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
