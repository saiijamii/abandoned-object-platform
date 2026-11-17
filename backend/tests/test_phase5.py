from app.runtime.config import CameraConfig
from app.runtime.phase5 import DeferredPhase5Processor
from app.runtime.sources import FramePacket
from app.storage.history import JsonlHistory


def test_fake_phase5_processor_keeps_runtime_hook(tmp_path) -> None:
    camera = CameraConfig("fake", True, "fake", None)
    processor = DeferredPhase5Processor(camera, {}, str(tmp_path))
    assert processor(FramePacket("fake", "session", 0, None, 0.0, 0)) == []


def test_jsonl_history_round_trip(tmp_path) -> None:
    history = JsonlHistory(tmp_path)
    history.append("camera", "session", "tracks.jsonl", {"track_id": "bag-1"})
    assert history.read("camera", "session", "tracks.jsonl") == [{"track_id": "bag-1"}]
