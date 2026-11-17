import time
from pathlib import Path

from ..detection.registry import create_detector
from ..events.recorder import EvidenceRecorder
from ..pipeline import PhaseTwoProcessor
from ..storage.history import JsonlHistory
from ..tracking.registry import create_tracker
from .processor import PassthroughProcessor


def _draw(frame, tracks):
    import cv2
    result = frame.copy()
    for track in tracks:
        x1, y1, x2, y2 = track.latest.bbox
        color = (23, 23, 23) if track.object_kind == "person" else (0, 112, 243)
        cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
        cv2.putText(result, f"{track.object_kind}:{track.track_id.rsplit(':', 1)[-1]}", (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 2)
    return result


class Phase5Processor:
    def __init__(self, camera, config: dict, storage_root: str = "storage", event_ledger=None) -> None:
        self.camera, self.config = camera, config
        self.detector = create_detector(config)
        self.tracker = create_tracker(camera.id, "pending", config)
        self.processor = PhaseTwoProcessor.create(camera.id, "pending", config)
        self.history = JsonlHistory(storage_root)
        self.recorder = EvidenceRecorder(Path(storage_root) / "cameras")
        self.event_ledger = event_ledger
        self.tracks = {}

    def __call__(self, packet):
        self._ensure_session(packet.session_id)
        started = time.perf_counter()
        detections = self.detector.detect(packet.frame)
        detector_ms = (time.perf_counter() - started) * 1000
        rows = [{"bbox": item.bbox, "confidence": item.confidence, "class_id": 0 if item.class_name == "person" else 1} for item in detections]
        started = time.perf_counter()
        frame_tracks = self.tracker.update(rows, packet.timestamp_s, packet.frame)
        tracker_ms = (time.perf_counter() - started) * 1000
        current = []
        for item in frame_tracks:
            track = self.tracks.setdefault(item.track_id, item)
            if track is not item:
                track.add(item.latest)
            current.append(track)
            self.history.append(packet.camera_id, packet.session_id, "tracks.jsonl", {"track_id": track.track_id, "object_type": track.object_kind, "timestamp_s": packet.timestamp_s, "bbox": list(track.latest.bbox), "confidence": track.latest.confidence})
        people = [item for item in current if item.object_kind == "person"]
        events = []
        raw = packet.frame.copy()
        annotated = _draw(packet.frame, current)
        for bag in [item for item in current if item.object_kind == "luggage"]:
            event = self.processor.update(bag, people, packet.timestamp_s, (packet.frame.shape[1], packet.frame.shape[0]))
            association = self.processor.association.associations.get(bag.track_id)
            if association:
                self.history.append(packet.camera_id, packet.session_id, "associations.jsonl", {"bag_track_id": bag.track_id, "owner_track_id": association.owner_track_id, "state": association.state.value, "timestamp_s": packet.timestamp_s, "episode": association.episode})
            if event and (self.event_ledger is None or self.event_ledger.claim_event(event)):
                owner = next((person for person in people if person.track_id == event.owner_track_id), None)
                events.append(self.recorder.record(event, raw, annotated, bag, owner))
        return [{"detector_ms": detector_ms, "tracker_ms": tracker_ms, "events": events}]

    def _ensure_session(self, session_id: str) -> None:
        if self.processor.session_id == session_id:
            return
        self.processor = PhaseTwoProcessor.create(self.camera.id, session_id, self.config)
        self.tracker = create_tracker(self.camera.id, session_id, self.config)
        self.tracks = {}


class DeferredPhase5Processor:
    def __init__(self, camera, config: dict, storage_root: str, event_ledger=None) -> None:
        self.camera, self.config, self.storage_root, self.event_ledger, self.delegate = camera, config, storage_root, event_ledger, None

    def __call__(self, packet):
        if self.delegate is None:
            self.delegate = PassthroughProcessor() if self.camera.source_kind == "fake" else Phase5Processor(self.camera, self.config, self.storage_root, self.event_ledger)
        return self.delegate(packet)


def phase5_factory(config: dict, storage_root: str):
    from .phase8 import PersistentEventLedger
    ledger = PersistentEventLedger(Path(storage_root) / "phase8" / "event_dedupe.jsonl")
    return lambda camera: DeferredPhase5Processor(camera, config, storage_root, ledger)
