from dataclasses import dataclass
from enum import Enum


class SearchDomain(str, Enum):
    PERSON = "person"
    BAG = "bag"


@dataclass(frozen=True)
class ObservationRecord:
    observation_id: str
    domain: SearchDomain
    camera_id: str
    session_id: str
    track_id: str
    event_id: str | None
    media_ts: float
    crop_path: str
    frame_path: str | None
    embedding: list[float]


@dataclass(frozen=True)
class CandidateMatch:
    observation_id: str
    domain: SearchDomain
    camera_id: str
    session_id: str
    track_id: str
    event_id: str | None
    media_ts: float
    crop_path: str
    frame_path: str | None
    similarity: float

    def as_dict(self) -> dict:
        return {**self.__dict__, "domain": self.domain.value}
