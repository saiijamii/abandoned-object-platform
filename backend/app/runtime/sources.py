import time
from dataclasses import dataclass
from typing import Any

from .config import CameraConfig, redact_uri, resolve_secret


@dataclass(frozen=True)
class FramePacket:
    camera_id: str
    session_id: str
    reconnect_epoch: int
    frame: Any
    timestamp_s: float
    frame_index: int


class Source:
    def open(self) -> None:
        pass

    def read(self) -> tuple[bool, Any, float]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class FakeSource(Source):
    def __init__(self, camera_id: str, frames: int = 30, fps: float = 10.0) -> None:
        self.camera_id, self.frames, self.fps = camera_id, frames, fps
        self.index = 0

    def read(self) -> tuple[bool, Any, float]:
        if self.index >= self.frames:
            return False, None, 0.0
        timestamp = self.index / self.fps
        self.index += 1
        return True, None, timestamp


class OpenCVSource(Source):
    def __init__(self, uri: str, live: bool = False) -> None:
        self.uri, self.live, self.capture = uri, live, None

    def open(self) -> None:
        import cv2
        self.capture = cv2.VideoCapture(self.uri)
        if self.live:
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.capture.isOpened():
            raise RuntimeError(f"cannot open source: {self.uri}")

    def read(self) -> tuple[bool, Any, float]:
        if self.capture is None:
            self.open()
        ok, frame = self.capture.read()
        if not ok:
            return False, None, time.monotonic()
        position_ms = self.capture.get(0)  # CAP_PROP_POS_MSEC without importing OpenCV at module load.
        return True, frame, position_ms / 1000 if position_ms > 0 else time.monotonic()

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None


class MP4Source(OpenCVSource):
    pass


class RTSPSource(OpenCVSource):
    def __init__(self, camera: CameraConfig) -> None:
        uri = resolve_secret(camera)
        if not uri:
            raise RuntimeError(f"missing RTSP secret environment variable: {camera.secret_env}")
        super().__init__(uri, live=True)


def create_source(camera: CameraConfig) -> Source:
    if camera.source_kind == "fake":
        return FakeSource(camera.id)
    if camera.source_kind == "mp4":
        if not camera.source_uri:
            raise ValueError(f"camera {camera.id} needs source.uri")
        return MP4Source(camera.source_uri)
    if camera.source_kind == "rtsp":
        return RTSPSource(camera)
    raise ValueError(f"unsupported source kind: {camera.source_kind}")
