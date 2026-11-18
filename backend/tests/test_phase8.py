import time
import pytest

from app.runtime.config import CameraConfig, SamplingConfig, camera_from_dict, camera_to_dict
from app.runtime.phase8 import LatestFrameQueue, PersistentEventLedger, Phase8CameraManager, TimestampGuard
from app.runtime.sources import FakeSource, FramePacket
from app.runtime import sources


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


def test_dynamic_camera_registry_add_replace_remove() -> None:
    manager = Phase8CameraManager([], lambda camera: lambda packet: None)
    camera = CameraConfig("dynamic", False, "fake", None)
    manager.add_camera(camera)
    assert [item.id for item in manager.camera_configs()] == ["dynamic"]
    manager.replace_camera("dynamic", CameraConfig("dynamic", False, "fake", None, sampling=SamplingConfig(queue_size=4)))
    assert manager.camera_configs()[0].sampling.queue_size == 4
    manager.remove_camera("dynamic")
    assert manager.camera_configs() == []


def test_dynamic_enabled_camera_joins_running_scheduler() -> None:
    seen = []
    manager = Phase8CameraManager([], lambda camera: lambda packet: seen.append(packet.camera_id))
    manager.start()
    manager.add_camera(CameraConfig("live", True, "fake", None))
    time.sleep(.1)
    manager.stop()
    assert "live" in seen


def test_camera_config_round_trip() -> None:
    camera = camera_from_dict({"id": "cam", "enabled": True, "source": {"kind": "http", "uri": "http://example.test/live"}, "sampling": {"queue_size": 2}})
    assert camera_from_dict(camera_to_dict(camera)) == camera


def test_source_check_always_closes(monkeypatch) -> None:
    class BrokenSource:
        closed = False
        def open(self): pass
        def read(self): raise RuntimeError("broken")
        def close(self): self.closed = True
    source = BrokenSource()
    monkeypatch.setattr(sources, "create_source", lambda camera: source)
    with pytest.raises(RuntimeError, match="broken"):
        sources.test_source(CameraConfig("test", False, "fake", None))
    assert source.closed
