import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.pipeline import PhaseTwoProcessor
from app.tracking.types import Track, TrackObservation


def main() -> None:
    processor = PhaseTwoProcessor.create("camera_01", "synthetic_demo", {})
    bag = Track("bag-1", "luggage")
    owner = Track("person-1", "person")
    event = None
    for timestamp in [0.0, .5, 1.0, 2.0, 3.0, 3.5, 4.0]:
        bag.add(TrackObservation(timestamp, (10, 10, 30, 30)))
        owner.add(TrackObservation(timestamp, (10, 35, 40, 100) if timestamp < 1 else (300, 10, 340, 80)))
        event = processor.update(bag, [owner], timestamp, (640, 480)) or event
    print(json.dumps(event.__dict__ if event else None, indent=2))


if __name__ == "__main__":
    main()
