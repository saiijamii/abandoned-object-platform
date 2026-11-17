import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import CameraConfig
from .sources import FramePacket, Source, create_source


@dataclass
class CameraHealth:
    camera_id: str
    session_id: str = field(default_factory=lambda: f"session-{uuid.uuid4().hex[:12]}")
    running: bool = False
    source_connected: bool = False
    frames_read: int = 0
    frames_processed: int = 0
    frames_dropped: int = 0
    reconnect_count: int = 0
    reconnect_epoch: int = 0
    last_source_timestamp: float | None = None
    last_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class CameraWorker:
    def __init__(self, config: CameraConfig, processor: Callable[[FramePacket], Any], source: Source | None = None) -> None:
        self.config = config
        self.processor = processor
        self.source = source or create_source(config)
        self.health = CameraHealth(config.id)
        self._queue: queue.Queue[FramePacket] = queue.Queue(maxsize=config.sampling.queue_size)
        self._stop = threading.Event()
        self._reader_thread: threading.Thread | None = None
        self._consumer_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.health.running:
            return
        self._stop.clear()
        self.health.running = True
        self._reader_thread = threading.Thread(target=self._read_loop, name=f"camera-reader-{self.config.id}", daemon=True)
        self._consumer_thread = threading.Thread(target=self._consume_loop, name=f"camera-worker-{self.config.id}", daemon=True)
        self._reader_thread.start()
        self._consumer_thread.start()

    def stop(self) -> None:
        self._stop.set()
        for thread in (self._reader_thread, self._consumer_thread):
            if thread:
                thread.join(timeout=2)
        self.source.close()
        self.health.running = False
        self.health.source_connected = False

    def _read_loop(self) -> None:
        try:
            self.source.open()
            self.health.source_connected = True
            frame_index = 0
            while not self._stop.is_set():
                ok, frame, timestamp = self.source.read()
                if not ok:
                    if self.config.source_kind == "fake" or self.config.source_kind == "mp4":
                        break
                    self._reconnect()
                    continue
                self.health.frames_read += 1
                self.health.last_source_timestamp = timestamp
                packet = FramePacket(self.config.id, self.health.session_id, self.health.reconnect_epoch, frame, timestamp, frame_index)
                frame_index += 1
                try:
                    self._queue.put_nowait(packet)
                except queue.Full:
                    if self.config.sampling.drop_policy != "drop_oldest":
                        self.health.frames_dropped += 1
                        continue
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait(packet)
                    self.health.frames_dropped += 1
        except Exception as exc:
            self.health.last_error = str(exc)
        finally:
            self.health.source_connected = False

    def _reconnect(self) -> None:
        self.health.reconnect_count += 1
        self.health.reconnect_epoch += 1
        self.source.close()
        delay = min(self.config.reconnect.maximum_seconds, self.config.reconnect.initial_seconds * self.config.reconnect.multiplier ** max(0, self.health.reconnect_count - 1))
        self._stop.wait(delay)
        if not self._stop.is_set():
            try:
                self.source.open()
                self.health.source_connected = True
            except Exception as exc:
                self.health.last_error = str(exc)

    def _consume_loop(self) -> None:
        while not self._stop.is_set() or not self._queue.empty():
            try:
                packet = self._queue.get(timeout=.1)
            except queue.Empty:
                continue
            if packet.frame_index % self.config.sampling.process_every_n_frames:
                continue
            try:
                self.processor(packet)
                self.health.frames_processed += 1
            except Exception as exc:
                self.health.last_error = str(exc)


class CameraManager:
    def __init__(self, cameras: list[CameraConfig], processor_factory: Callable[[CameraConfig], Callable[[FramePacket], Any]]) -> None:
        self.workers = {camera.id: CameraWorker(camera, processor_factory(camera)) for camera in cameras}

    def start(self) -> None:
        for worker in self.workers.values():
            if worker.config.enabled:
                worker.start()

    def stop(self) -> None:
        for worker in self.workers.values():
            worker.stop()

    def start_camera(self, camera_id: str) -> dict:
        worker = self._get(camera_id)
        worker.start()
        return worker.health.as_dict()

    def stop_camera(self, camera_id: str) -> dict:
        worker = self._get(camera_id)
        worker.stop()
        return worker.health.as_dict()

    def restart_camera(self, camera_id: str) -> dict:
        self.stop_camera(camera_id)
        return self.start_camera(camera_id)

    def health(self, camera_id: str | None = None) -> list[dict] | dict:
        if camera_id:
            return self._get(camera_id).health.as_dict()
        return [worker.health.as_dict() for worker in self.workers.values()]

    def _get(self, camera_id: str) -> CameraWorker:
        if camera_id not in self.workers:
            raise KeyError(camera_id)
        return self.workers[camera_id]
