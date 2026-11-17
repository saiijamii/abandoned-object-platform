import time

from app.runtime.config import CameraConfig, SamplingConfig
from app.runtime.phase8 import LatestFrameQueue, PersistentEventLedger, Phase8CameraManager, TimestampGuard
from app.runtime.sources import FakeSource, FramePacket


def test_latest_queue_keeps_newest_frame() -> None:
    queue = LatestFrameQueue(2)
    for index in range(3):
        queue.put(FramePacket("cam", "session", 0, None, float(index), index))
    assert queue.dropped == 1
    assert queue.get_nowait().frame_index == 1
    assert queue.get_nowait().frame_index == 2


def test_timestamp_guard_clamps_out_of_order() -> None:
    guard = TimestampGuard()
    first, changed = guard.apply(FramePacket("cam", "session", 0, None, 2.0, 0))
    second, changed = guard.apply(FramePacket("cam", "session", 0, None, 1.0, 1))
    assert first.timestamp_s == 2.0
    assert second.timestamp_s == 2.0
    assert changed


def test_event_ledger_survives_restart(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    assert PersistentEventLedger(path).claim("cam", "bag-1", 4.0)
    assert not PersistentEventLedger(path).claim("cam", "bag-1", 4.0)


def test_phase8_manager_processes_two_cameras_fairly() -> None:
    cameras = [
        CameraConfig("a", True, "fake", None, sampling=SamplingConfig(queue_size=2)),
        CameraConfig("b", True, "fake", None, sampling=SamplingConfig(queue_size=2)),
    ]
    seen = []
    manager = Phase8CameraManager(cameras, lambda camera: lambda packet: seen.append((camera.id, packet.frame_index)))
    manager.workers["a"]._source = FakeSource("a", frames=4)
    manager.workers["b"]._source = FakeSource("b", frames=4)
    manager.start()
    time.sleep(.1)
    manager.stop()
    assert {camera_id for camera_id, _ in seen} == {"a", "b"}
