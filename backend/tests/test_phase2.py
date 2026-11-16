from app.ownership.association import Association, AssociationEngine, AssociationState
from app.pipeline import PhaseTwoProcessor
from app.tracking.types import Track, TrackObservation


def track(identifier, kind, timestamp, bbox, previous=()):
    value = Track(identifier, kind, [TrackObservation(t, box) for t, box in previous] or [TrackObservation(timestamp, bbox)])
    return value


def test_temporal_association_and_two_second_event() -> None:
    processor = PhaseTwoProcessor.create("camera_01", "session_01", {"ownership": {"association_seconds": .5}, "alert": {"min_stationary_observations": 3}})
    bag = track("bag", "luggage", 0, (10, 10, 30, 30), [(0.0, (10, 10, 30, 30)), (.5, (10, 10, 30, 30)), (1.0, (10, 10, 30, 30)), (2.0, (10, 10, 30, 30)), (2.5, (10, 10, 30, 30)), (3.0, (10, 10, 30, 30))])
    owner = track("person", "person", 3.0, (300, 10, 340, 80))
    assert processor.update(bag, [track("person", "person", 0, (10, 35, 40, 100))], 0.0, (640, 480)) is None
    assert processor.update(bag, [track("person", "person", .5, (10, 35, 40, 100))], .5, (640, 480)) is None
    assert processor.update(bag, [owner], 1.0, (640, 480)) is None
    assert processor.update(bag, [owner], 2.0, (640, 480)) is None
    assert processor.update(bag, [owner], 3.0, (640, 480)) is not None
    assert processor.update(bag, [owner], 4.0, (640, 480)) is None


def test_ambiguous_owner_not_assigned() -> None:
    engine = AssociationEngine()
    bag = track("bag", "luggage", 0, (100, 100, 120, 120))
    people = [track("p1", "person", 0, (90, 100, 110, 160)), track("p2", "person", 0, (110, 100, 130, 160))]
    result = engine.update(bag, people, 0, (640, 480))
    assert result.state == AssociationState.AMBIGUOUS
    assert result.owner_track_id is None


def test_event_rearms_after_owner_returns() -> None:
    engine = AssociationEngine()
    association = engine.associations.setdefault("bag", Association("bag"))
    association.state = AssociationState.SEPARATED
    association.owner_track_id = "person"
    association.separated_since_s = 0
    bag = track("bag", "luggage", 3, (10, 10, 30, 30))
    person = track("person", "person", 3, (10, 35, 40, 100))
    engine.update(bag, [person], 3, (640, 480))
    assert association.episode == 1
