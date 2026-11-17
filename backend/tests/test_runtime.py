import time

from app.runtime.config import CameraConfig, SamplingConfig
from app.runtime.sources import FakeSource, FramePacket, redact_uri
from app.runtime.worker import CameraManager, CameraWorker


def test_secret_redaction() -> None:
    assert redact_uri("rtsp://admin:secret@example.com/stream") == "rtsp://***:***@example.com/stream"


def test_fake_worker_processes_bounded_source() -> None:
    packets: list[FramePacket] = []
    camera = CameraConfig("fake", True, "fake", None, sampling=SamplingConfig(queue_size=2))
    worker = CameraWorker(camera, packets.append, FakeSource("fake", frames=5, fps=10))
    worker.start()
    time.sleep(.1)
    worker.stop()
    assert worker.health.frames_read == 5
    assert worker.health.frames_processed + worker.health.frames_dropped <= worker.health.frames_read
    assert all(packet.camera_id == "fake" for packet in packets)


def test_camera_manager_keeps_sessions_separate() -> None:
    cameras = [CameraConfig("a", True, "fake", None), CameraConfig("b", True, "fake", None)]
    manager = CameraManager(cameras, lambda _camera: lambda _packet: None)
    manager.start()
    time.sleep(.05)
    health = manager.health()
    manager.stop()
    assert {item["camera_id"] for item in health} == {"a", "b"}
    assert len({item["session_id"] for item in health}) == 2
