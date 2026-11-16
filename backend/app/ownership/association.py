from dataclasses import dataclass
from enum import Enum
from math import hypot

from ..tracking.types import Track


class AssociationState(str, Enum):
    UNASSIGNED = "unassigned"
    CANDIDATE = "candidate"
    AMBIGUOUS = "ambiguous"
    ASSOCIATED = "associated"
    SEPARATED = "separated"


@dataclass
class Association:
    bag_track_id: str
    owner_track_id: str | None = None
    state: AssociationState = AssociationState.UNASSIGNED
    candidate_since_s: float | None = None
    separated_since_s: float | None = None
    episode: int = 0


def _center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


class AssociationEngine:
    def __init__(self, association_seconds: float = .5, max_distance_ratio: float = .18, ambiguous_margin_ratio: float = .025, separation_distance_ratio: float = .24) -> None:
        self.association_seconds = association_seconds
        self.max_distance_ratio = max_distance_ratio
        self.ambiguous_margin_ratio = ambiguous_margin_ratio
        self.separation_distance_ratio = separation_distance_ratio
        self.associations: dict[str, Association] = {}

    def update(self, bag: Track, people: list[Track], timestamp_s: float, frame_size: tuple[int, int]) -> Association:
        association = self.associations.setdefault(bag.track_id, Association(bag.track_id))
        if not people:
            return association
        width, height = frame_size
        diagonal = max(1.0, hypot(width, height))
        bag_center = _center(bag.latest.bbox)
        ranked = sorted(((hypot(bag_center[0] - _center(person.latest.bbox)[0], bag_center[1] - _center(person.latest.bbox)[1]) / diagonal, person) for person in people), key=lambda item: item[0])
        best_distance, best_person = ranked[0]
        second_distance = ranked[1][0] if len(ranked) > 1 else None
        ambiguous = second_distance is not None and second_distance - best_distance <= self.ambiguous_margin_ratio
        if ambiguous or best_distance > self.max_distance_ratio:
            if association.state == AssociationState.ASSOCIATED:
                association.state = AssociationState.SEPARATED
                if association.separated_since_s is None:
                    association.separated_since_s = timestamp_s
            elif association.state not in {AssociationState.SEPARATED, AssociationState.AMBIGUOUS}:
                association.state = AssociationState.AMBIGUOUS if ambiguous else AssociationState.UNASSIGNED
            return association
        if association.owner_track_id != best_person.track_id or association.state in {AssociationState.UNASSIGNED, AssociationState.AMBIGUOUS}:
            association.owner_track_id = best_person.track_id
            association.candidate_since_s = timestamp_s
            association.state = AssociationState.CANDIDATE
            association.separated_since_s = None
            return association
        candidate_since = association.candidate_since_s if association.candidate_since_s is not None else timestamp_s
        if association.state == AssociationState.CANDIDATE and timestamp_s - candidate_since >= self.association_seconds:
            association.state = AssociationState.ASSOCIATED
        elif association.state == AssociationState.SEPARATED:
            association.state = AssociationState.ASSOCIATED
            association.separated_since_s = None
            association.episode += 1
        return association

    def separation_elapsed(self, bag: Track, people: list[Track], association: Association, timestamp_s: float, frame_size: tuple[int, int]) -> float:
        if association.owner_track_id is None:
            return 0.0
        owner = next((person for person in people if person.track_id == association.owner_track_id), None)
        if owner is None:
            return 0.0
        diagonal = max(1.0, hypot(frame_size[0], frame_size[1]))
        distance = hypot(_center(bag.latest.bbox)[0] - _center(owner.latest.bbox)[0], _center(bag.latest.bbox)[1] - _center(owner.latest.bbox)[1]) / diagonal
        if association.state == AssociationState.ASSOCIATED and distance > self.separation_distance_ratio:
            association.state = AssociationState.SEPARATED
            association.separated_since_s = timestamp_s
        if association.state == AssociationState.SEPARATED and association.separated_since_s is not None:
            return timestamp_s - association.separated_since_s
        return 0.0
