from dataclasses import dataclass

from .events.state_machine import CandidateEvent, SeparationEventMachine
from .ownership.association import AssociationEngine
from .tracking.types import Track


@dataclass
class PhaseTwoProcessor:
    camera_id: str
    session_id: str
    association: AssociationEngine
    events: SeparationEventMachine

    @classmethod
    def create(cls, camera_id: str, session_id: str, config: dict) -> "PhaseTwoProcessor":
        ownership = config.get("ownership", {})
        alert = config.get("alert", {})
        return cls(camera_id, session_id, AssociationEngine(
            association_seconds=float(ownership.get("association_seconds", .5)),
            max_distance_ratio=float(ownership.get("association_max_distance_ratio", .18)),
            ambiguous_margin_ratio=float(ownership.get("ambiguous_owner_margin_ratio", .025)),
            separation_distance_ratio=float(ownership.get("separation_distance_ratio", .24)),
        ), SeparationEventMachine(session_id=session_id, camera_id=camera_id, **{
            "separation_seconds": float(alert.get("separation_seconds", 2.0)),
            "stationary_window_seconds": float(alert.get("stationary_window_seconds", 1.0)),
            "stationary_max_movement_ratio": float(alert.get("stationary_max_movement_ratio", .02)),
            "min_stationary_observations": int(alert.get("min_stationary_observations", 3)),
        }))

    def update(self, bag: Track, people: list[Track], timestamp_s: float, frame_size: tuple[int, int]) -> CandidateEvent | None:
        state = self.association.update(bag, people, timestamp_s, frame_size)
        elapsed = self.association.separation_elapsed(bag, people, state, timestamp_s, frame_size)
        return self.events.update(bag, state, elapsed, timestamp_s, frame_size)
