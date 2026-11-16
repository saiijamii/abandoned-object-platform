import json
from pathlib import Path
from typing import Any

import cv2

from .state_machine import CandidateEvent
from ..tracking.types import Track


class EvidenceRecorder:
    def __init__(self, root: str | Path = "storage") -> None:
        self.root = Path(root)

    @staticmethod
    def _crop(frame: Any, bbox: tuple[int, int, int, int]) -> Any:
        height, width = frame.shape[:2]
        x1, y1 = max(0, bbox[0]), max(0, bbox[1])
        x2, y2 = min(width, bbox[2]), min(height, bbox[3])
        return frame[y1:y2, x1:x2]

    def record(self, event: CandidateEvent, raw_frame: Any, annotated_frame: Any, bag: Track, owner: Track | None = None) -> dict[str, Any]:
        directory = self.root / event.camera_id / event.session_id / "events" / event.event_id
        directory.mkdir(parents=True, exist_ok=True)
        raw_path = directory / "frame.jpg"
        annotated_path = directory / "annotated.jpg"
        bag_path = directory / "bag_crop.jpg"
        owner_path = directory / "owner_crop.jpg"
        cv2.imwrite(str(raw_path), raw_frame)
        cv2.imwrite(str(annotated_path), annotated_frame)
        cv2.imwrite(str(bag_path), self._crop(raw_frame, bag.latest.bbox))
        owner_written = bool(owner and cv2.imwrite(str(owner_path), self._crop(raw_frame, owner.latest.bbox)))
        metadata = {**event.__dict__, "raw_snapshot_path": str(raw_path), "annotated_snapshot_path": str(annotated_path), "bag_crop_path": str(bag_path), "owner_crop_path": str(owner_path) if owner_written else None}
        (directory / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata
