from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrackObservation:
    timestamp_s: float
    bbox: tuple[int, int, int, int]
    confidence: float = 1.0


@dataclass
class Track:
    track_id: str
    object_kind: str
    observations: list[TrackObservation] = field(default_factory=list)

    @property
    def latest(self) -> TrackObservation:
        if not self.observations:
            raise ValueError("track has no observations")
        return self.observations[-1]

    def add(self, observation: TrackObservation) -> None:
        if self.observations and observation.timestamp_s < self.latest.timestamp_s:
            raise ValueError("track timestamps must be monotonic")
        self.observations.append(observation)
