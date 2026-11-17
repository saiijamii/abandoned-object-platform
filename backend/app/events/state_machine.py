from dataclasses import dataclass

from ..ownership.association import Association, AssociationState
from ..tracking.types import Track


@dataclass(frozen=True)
class CandidateEvent:
    event_id: str
    event_type: str
    camera_id: str
    session_id: str
    bag_track_id: str
    owner_track_id: str | None
    timestamp_s: float
    separation_seconds: float
    bag_stationary: bool
    dedup_key: str
    separation_episode_start_media_ts: float | None = None


class SeparationEventMachine:
    def __init__(self, camera_id: str, session_id: str, separation_seconds: float = 2.0, stationary_window_seconds: float = 1.0, stationary_max_movement_ratio: float = .02, min_stationary_observations: int = 3) -> None:
        self.camera_id = camera_id
        self.session_id = session_id
        self.separation_seconds = separation_seconds
        self.stationary_window_seconds = stationary_window_seconds
        self.stationary_max_movement_ratio = stationary_max_movement_ratio
        self.min_stationary_observations = min_stationary_observations
        self.emitted: set[str] = set()

    @staticmethod
    def _center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

    def is_stationary(self, bag: Track, timestamp_s: float, frame_size: tuple[int, int]) -> bool:
        observations = [item for item in bag.observations if timestamp_s - item.timestamp_s <= self.stationary_window_seconds]
        if len(observations) < self.min_stationary_observations:
            return False
        diagonal = max(1.0, (frame_size[0] ** 2 + frame_size[1] ** 2) ** .5)
        start = self._center(observations[0].bbox)
        end = self._center(observations[-1].bbox)
        return ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** .5 / diagonal <= self.stationary_max_movement_ratio

    def update(self, bag: Track, association: Association, separation_seconds: float, timestamp_s: float, frame_size: tuple[int, int]) -> CandidateEvent | None:
        if association.state != AssociationState.SEPARATED or separation_seconds < self.separation_seconds:
            return None
        dedup_key = f"{self.camera_id}|{self.session_id}|{bag.track_id}|episode:{association.episode}"
        if dedup_key in self.emitted or not self.is_stationary(bag, timestamp_s, frame_size):
            return None
        self.emitted.add(dedup_key)
        return CandidateEvent(
            event_id=f"evt_{len(self.emitted):08d}",
            event_type="unattended_luggage_candidate",
            camera_id=self.camera_id,
            session_id=self.session_id,
            bag_track_id=bag.track_id,
            owner_track_id=association.owner_track_id,
            timestamp_s=timestamp_s,
            separation_seconds=separation_seconds,
            bag_stationary=True,
            dedup_key=dedup_key,
            separation_episode_start_media_ts=association.separated_since_s,
        )
