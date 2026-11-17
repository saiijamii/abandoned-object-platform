from dataclasses import dataclass
from typing import Any

from .types import Track, TrackObservation


@dataclass(frozen=True)
class TrackerConfig:
    backend: str = "bytetrack"
    max_lost_frames: int = 30
    use_embeddings: bool = False
    use_cmc: bool = False


class BoxMOTTracker:
    """Optional BoxMOT boundary. Tracker state belongs to one camera session."""

    def __init__(self, camera_id: str, session_id: str, config: TrackerConfig) -> None:
        if config.backend not in {"bytetrack", "botsort"}:
            raise ValueError("tracker backend must be bytetrack or botsort")
        try:
            from boxmot import BotSort, ByteTrack
        except ImportError as exc:
            try:
                from boxmot import BotSort, BYTETracker as ByteTrack
            except ImportError:
                raise RuntimeError("Install tracker dependencies with pip install -r backend/requirements-phase2.txt") from exc
        tracker_type = ByteTrack if config.backend == "bytetrack" else BotSort
        self.tracker = tracker_type()
        self.camera_id = camera_id
        self.session_id = session_id
        self.config = config

    def update(self, detections: list[dict[str, Any]], timestamp_s: float, frame: Any) -> list[Track]:
        # BoxMOT versions expose different update signatures. Keep this adapter
        # narrow; callers only receive session-scoped Track values.
        import numpy as np

        rows = np.asarray([[*d["bbox"], d["confidence"], d.get("class_id", 0)] for d in detections], dtype=float).reshape((-1, 6))
        try:
            raw = self.tracker.update(rows, frame, timestamp_s=timestamp_s)
        except TypeError:
            raw = self.tracker.update(rows, frame)
        tracks: list[Track] = []
        for row in raw:
            x1, y1, x2, y2, track_id, class_id = row[:6]
            kind = "person" if int(class_id) == 0 else "luggage"
            public_id = f"{self.camera_id}:{self.session_id}:{kind}:{int(track_id):06d}"
            tracks.append(Track(public_id, kind, [TrackObservation(timestamp_s, (round(x1), round(y1), round(x2), round(y2)))]))
        return tracks
