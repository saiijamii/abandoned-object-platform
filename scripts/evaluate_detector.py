"""Phase One detector evaluation CLI."""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def load_truth(path: str) -> dict[int, list[Detection]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {int(frame["frame_index"]): [Detection(item["class_name"], 1.0, tuple(item["bbox"])) for item in frame.get("objects", [])] for frame in payload.get("frames", [])}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate normalized detector output.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--output", default="storage/evaluation/report.json")
    args = parser.parse_args()
    import cv2
    from app.core.config import load_config
    from app.detection.registry import create_detector
    from app.detection.types import Detection
    from app.evaluation import precision_recall, score_frame

    for value in (args.input, args.config, args.ground_truth):
        if not Path(value).exists():
            raise SystemExit(f"missing input: {value}")
    truth = load_truth(args.ground_truth)
    detector = create_detector(load_config(args.config))
    capture = cv2.VideoCapture(args.input)
    counts = {}
    timings = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index in truth:
            started = time.perf_counter()
            predictions = detector.detect(frame)
            timings.append((time.perf_counter() - started) * 1000)
            frame_counts = score_frame(predictions, truth[frame_index])
            for key, value in frame_counts.items():
                counts[key] = counts.get(key, 0) + value
        frame_index += 1
    capture.release()
    counter = __import__("collections").Counter(counts)
    timings.sort()
    p95 = timings[min(len(timings) - 1, round(len(timings) * .95) - 1)] if timings else 0.0
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    report = {"input": args.input, "config": args.config, "ground_truth": args.ground_truth, "frames_evaluated": len(truth), "metrics": {"person": precision_recall(counter, "person"), "luggage": precision_recall(counter, "luggage")}, "performance": {"median_inference_ms": timings[len(timings) // 2] if timings else 0.0, "p95_inference_ms": p95, "processing_fps": 1000 / (sum(timings) / len(timings)) if timings and sum(timings) else 0.0}}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
