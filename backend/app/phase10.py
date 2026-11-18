"""Deterministic release-candidate checks for the current Phase 8 runtime."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from .runtime.config import CameraConfig, ReconnectConfig, SamplingConfig
from .runtime.phase8 import Phase8CameraManager
from .runtime.sources import FakeSource, FramePacket, Source


@dataclass
class SmokeResult:
    camera_count: int
    duration_seconds: float
    frames_read: int
    frames_processed: int
    frames_dropped: int
    processed_fps: float
    max_queue_depth: int
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _configs(camera_count: int, queue_size: int = 2) -> list[CameraConfig]:
    return [CameraConfig(f"phase10-{index}", True, "fake", None, sampling=SamplingConfig(queue_size=queue_size)) for index in range(camera_count)]


def run_smoke(camera_count: int = 2, frames: int = 30, queue_size: int = 2) -> SmokeResult:
    cameras = _configs(camera_count, queue_size)
    manager = Phase8CameraManager(cameras, lambda _camera: lambda _packet: None)
    for camera in cameras:
        manager.workers[camera.id]._source = FakeSource(camera.id, frames=frames, fps=30.0)
    started = time.perf_counter()
    manager.start()
    deadline = time.monotonic() + 5
    max_queue_depth = 0
    while time.monotonic() < deadline and any(worker.health.frames_read < frames for worker in manager.workers.values()):
        max_queue_depth = max(max_queue_depth, *(worker.queue.depth for worker in manager.workers.values()))
        time.sleep(.01)
    manager.stop()
    duration_seconds = max(time.perf_counter() - started, 0.001)
    health = manager.health()
    return SmokeResult(
        camera_count=camera_count,
        duration_seconds=round(duration_seconds, 3),
        frames_read=sum(item["frames_read"] for item in health),
        frames_processed=sum(item["frames_processed"] for item in health),
        frames_dropped=sum(item["frames_dropped"] for item in health),
        processed_fps=round(sum(item["frames_processed"] for item in health) / duration_seconds, 3),
        max_queue_depth=max_queue_depth,
        status="pass" if all(item["frames_read"] == frames for item in health) else "fail",
    )


class FlakySource(Source):
    """Source fails once, then emits frames. Used only by failure drills."""

    def __init__(self, frames: int = 3) -> None:
        self.frames = frames
        self.index = 0
        self.opens = 0

    def open(self) -> None:
        self.opens += 1

    def read(self) -> tuple[bool, Any, float]:
        if self.opens == 1:
            return False, None, 0.0
        if self.index >= self.frames:
            return False, None, 0.0
        timestamp = self.index / 10
        self.index += 1
        return True, None, timestamp


def run_reconnect_drill() -> dict[str, Any]:
    config = CameraConfig("phase10-flaky", True, "rtsp", None, reconnect=ReconnectConfig(initial_seconds=.01, maximum_seconds=.02, multiplier=1.0, jitter_seconds=0, jitter_fraction=0))
    source = FlakySource()
    processed: list[FramePacket] = []
    from .runtime.worker import CameraWorker
    worker = CameraWorker(config, processed.append, source)
    worker.start()
    time.sleep(.15)
    worker.stop()
    return {"reconnect_count": worker.health.reconnect_count, "frames_processed": worker.health.frames_processed, "status": "pass" if worker.health.reconnect_count >= 1 and worker.health.frames_processed >= 1 else "fail"}
