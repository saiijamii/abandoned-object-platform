import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def serialize_track(track) -> dict:
    return {
        "track_id": track.track_id,
        "object_kind": track.object_kind,
        "observations": [
            {"timestamp_s": item.timestamp_s, "bbox": list(item.bbox), "confidence": item.confidence}
            for item in track.observations
        ],
    }


def draw_tracks(frame, tracks):
    import cv2
    for track in tracks:
        x1, y1, x2, y2 = track.latest.bbox
        color = (23, 23, 23) if track.object_kind == "person" else (0, 112, 243)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{track.object_kind}:{track.track_id.rsplit(':', 1)[-1]}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 2)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase Three detector, tracker, ownership, and evidence pipeline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--storage-root", default="storage")
    args = parser.parse_args()

    import cv2
    import yaml
    from app.detection.registry import create_detector
    from app.events.recorder import EvidenceRecorder
    from app.metrics import timing_metrics
    from app.pipeline import PhaseTwoProcessor
    from app.storage.json_store import JsonStore
    from app.tracking.registry import create_tracker

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    detector = create_detector(config)
    tracker = create_tracker(args.camera_id, args.session_id, config)
    processor = PhaseTwoProcessor.create(args.camera_id, args.session_id, config)
    recorder = EvidenceRecorder(args.storage_root)
    store = JsonStore(Path(args.storage_root) / "index")

    capture = cv2.VideoCapture(args.input)
    if not capture.isOpened():
        raise SystemExit(f"cannot open video: {args.input}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise SystemExit(f"cannot open output video: {args.output}")

    tracks = {}
    detector_times, tracker_times = [], []
    frames_read = frames_written = frames_with_person = frames_with_bag = person_boxes = bag_boxes = 0
    events = []
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frames_read += 1
            position_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
            timestamp_s = position_ms / 1000 if position_ms > 0 else frame_index / fps
            started = time.perf_counter()
            detections = detector.detect(frame)
            detector_times.append((time.perf_counter() - started) * 1000)
            person_detections = [item for item in detections if item.class_name == "person"]
            bag_detections = [item for item in detections if item.class_name == "luggage"]
            frames_with_person += bool(person_detections)
            frames_with_bag += bool(bag_detections)
            person_boxes += len(person_detections)
            bag_boxes += len(bag_detections)
            tracker_input = [{"bbox": item.bbox, "confidence": item.confidence, "class_id": 0 if item.class_name == "person" else 1} for item in detections]
            started = time.perf_counter()
            frame_tracks = tracker.update(tracker_input, timestamp_s, frame)
            tracker_times.append((time.perf_counter() - started) * 1000)
            current = []
            for item in frame_tracks:
                existing = tracks.setdefault(item.track_id, item)
                if existing is not item:
                    existing.add(item.latest)
                current.append(existing)
            people = [item for item in current if item.object_kind == "person"]
            bags = [item for item in current if item.object_kind == "luggage"]
            raw_frame = frame.copy()
            annotated = draw_tracks(frame.copy(), current)
            for bag in bags:
                event = processor.update(bag, people, timestamp_s, (width, height))
                if event:
                    owner = next((person for person in people if person.track_id == event.owner_track_id), None)
                    metadata = recorder.record(event, raw_frame, annotated, bag, owner)
                    store.put("events", event.event_id, metadata)
                    events.append(metadata)
            writer.write(annotated)
            frames_written += 1
            frame_index += 1
    finally:
        capture.release()
        writer.release()

    for track in tracks.values():
        store.put("tracks", track.track_id.replace(":", "_"), serialize_track(track))
    metrics = {
        "input": args.input,
        "output": str(output_path),
        "camera_id": args.camera_id,
        "session_id": args.session_id,
        "source_fps": fps,
        "frames_read": frames_read,
        "frames_written": frames_written,
        "frames_with_person_detection": frames_with_person,
        "frames_with_bag_detection": frames_with_bag,
        "person_boxes": person_boxes,
        "bag_boxes": bag_boxes,
        "person_detection_frame_rate": frames_with_person / frames_read if frames_read else 0.0,
        "bag_detection_frame_rate": frames_with_bag / frames_read if frames_read else 0.0,
        "detector_timing": timing_metrics(detector_times),
        "tracker_timing": timing_metrics(tracker_times),
        "events_emitted": len(events),
        "tracks": len(tracks),
        "warning": "bag_detection_frame_rate is not recall; use evaluate_recall.py with annotations",
    }
    metrics_path = Path(args.metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
