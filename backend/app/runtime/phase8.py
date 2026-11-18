"""Phase 8 multi-camera ingestion and fair inference runtime."""

from __future__ import annotations

import json
import queue
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from .config import CameraConfig
from .sources import FramePacket, Source, create_source


class LatestFrameQueue:
    """Bounded queue that keeps newest frame when inference falls behind."""

    def __init__(self, maxsize: int = 2) -> None:
        self.maxsize = max(1, maxsize)
        self._items: deque[FramePacket] = deque(maxlen=self.maxsize)
        self._lock = threading.Lock()
        self.dropped = 0

    def put(self, packet: FramePacket) -> None:
        with self._lock:
            if len(self._items) == self.maxsize:
                self._items.popleft()
                self.dropped += 1
            self._items.append(packet)

    def get_nowait(self) -> FramePacket:
        with self._lock:
            if not self._items:
                raise queue.Empty
            return self._items.popleft()

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class TimestampGuard:
    def __init__(self) -> None:
        self._last: dict[tuple[str, str], float] = {}

    def apply(self, packet: FramePacket) -> tuple[FramePacket, bool]:
        key = (packet.camera_id, packet.session_id)
        previous = self._last.get(key)
        timestamp = packet.timestamp_s
        out_of_order = previous is not None and timestamp < previous
        if previous is not None and timestamp < previous:
            timestamp = previous
        self._last[key] = timestamp
        return replace(packet, timestamp_s=timestamp), out_of_order


class ReconnectBackoff:
    def __init__(self, camera: CameraConfig) -> None:
        self.config = camera.reconnect
        self.attempt = 0

    def next_delay(self) -> float:
        base = min(self.config.maximum_seconds, self.config.initial_seconds * self.config.multiplier ** self.attempt)
        self.attempt += 1
        fraction = max(0.0, self.config.jitter_fraction)
        jitter = base * fraction if fraction else self.config.jitter_seconds
        return max(0.0, min(self.config.maximum_seconds, base + random.uniform(-jitter, jitter)))

    def reset(self) -> None:
        self.attempt = 0


class PersistentEventLedger:
    """Append-only dedupe ledger. File lock is process-local; use DB locking for multi-process workers."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._keys: set[str] = set()
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._keys.add(json.loads(line)["key"])

    def claim(self, camera_id: str, bag_track_id: str, episode_start_media_ts: float | str) -> bool:
        key = f"{camera_id}|{bag_track_id}|{episode_start_media_ts}"
        return self._claim_key(key)

    def claim_event(self, event: Any) -> bool:
        start = event.separation_episode_start_media_ts
        return self.claim(event.camera_id, event.bag_track_id, start if start is not None else event.timestamp_s)

    def _claim_key(self, key: str) -> bool:
        with self._lock:
            if key in self._keys:
                return False
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"key": key}) + "\n")
            self._keys.add(key)
            return True


@dataclass
class Phase8Health:
    camera_id: str
    enabled: bool = True
    source_type: str = "fake"
    session_id: str = field(default_factory=lambda: f"session-{uuid.uuid4().hex[:12]}")
    running: bool = False
    source_connected: bool = False
    state: str = "stopped"
    frames_read: int = 0
    frames_processed: int = 0
    frames_dropped: int = 0
    reconnect_count: int = 0
    reconnect_epoch: int = 0
    decoded_fps: float = 0.0
    processed_fps: float = 0.0
    inference_latency_ms: float = 0.0
    queue_depth: int = 0
    dropped_frames_total: int = 0
    last_source_timestamp: float | None = None
    last_media_timestamp: float | None = None
    stream_lag_ms: float | None = None
    last_frame_age_ms: float | None = None
    last_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class Phase8CameraWorker:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.health = Phase8Health(config.id, config.enabled, config.source_kind)
        self.queue = LatestFrameQueue(config.sampling.queue_size)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._source: Source | None = None
        self._frame_index = 0
        self._backoff = ReconnectBackoff(config)
        self.last_arrival_monotonic: float | None = None

    def start(self) -> None:
        if self.health.running:
            return
        self._stop.clear()
        self.health.running = True
        self.health.state = "starting"
        self._thread = threading.Thread(target=self._read_loop, name=f"phase8-reader-{self.config.id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._close_source()
        self.health.running = False
        self.health.source_connected = False
        self.health.state = "stopped"

    def _new_session(self) -> None:
        self.health.session_id = f"session-{uuid.uuid4().hex[:12]}"
        self.health.reconnect_epoch += 1
        self.queue.clear()

    def _open_source(self) -> bool:
        try:
            if self._source is None:
                self._source = create_source(self.config)
            self._source.open()
            self.health.source_connected = True
            self.health.state = "connected"
            self._backoff.reset()
            return True
        except Exception as exc:
            self.health.last_error = str(exc)
            self.health.source_connected = False
            self.health.state = "reconnecting"
            self._close_source()
            return False

    def _close_source(self) -> None:
        if self._source:
            self._source.close()
            self._source = None

    def _read_loop(self) -> None:
        first_open = True
        while not self._stop.is_set():
            if not self._open_source():
                self._stop.wait(self._backoff.next_delay())
                continue
            if not first_open:
                self._new_session()
            first_open = False
            while not self._stop.is_set() and self._source:
                try:
                    ok, frame, timestamp = self._source.read()
                except Exception as exc:
                    ok, frame, timestamp = False, None, time.monotonic()
                    self.health.last_error = str(exc)
                if not ok:
                    self.health.source_connected = False
                    self.health.state = "reconnecting" if self.config.source_kind == "rtsp" else "ended"
                    self._close_source()
                    if self.config.source_kind != "rtsp":
                        return
                    self.health.reconnect_count += 1
                    self._stop.wait(self._backoff.next_delay())
                    break
                self.health.frames_read += 1
                self.health.last_source_timestamp = timestamp
                self.health.last_media_timestamp = timestamp
                self.last_arrival_monotonic = time.monotonic()
                packet = FramePacket(self.config.id, self.health.session_id, self.health.reconnect_epoch, frame, timestamp, self._frame_index)
                self._frame_index += 1
                before = self.queue.dropped
                self.queue.put(packet)
                self.health.frames_dropped += self.queue.dropped - before
                self.health.dropped_frames_total = self.health.frames_dropped
        self._close_source()


class Phase8CameraManager:
    def __init__(self, cameras: list[CameraConfig], processor_factory: Callable[[CameraConfig], Callable[[FramePacket], Any]], storage_root: str | Path = "storage", runtime: dict[str, Any] | None = None) -> None:
        self._processor_factory = processor_factory
        self.workers = {camera.id: Phase8CameraWorker(camera) for camera in cameras}
        self.processors = {camera.id: processor_factory(camera) for camera in cameras}
        self._order = list(self.workers)
        self._cursor = 0
        self._timestamp_guard = TimestampGuard()
        self._stop = threading.Event()
        self._scheduler: threading.Thread | None = None
        self._registry_lock = threading.RLock()
        self._running = False
        self._max_gap = float((runtime or {}).get("max_continuity_gap_seconds", .75))
        self._last_processed: dict[str, float] = {}
        self._processed_times: dict[str, deque[float]] = {camera.id: deque() for camera in cameras}
        self._decoded_times: dict[str, deque[float]] = {camera.id: deque() for camera in cameras}

    def start(self) -> None:
        self._running = True
        self._stop.clear()
        for worker in list(self.workers.values()):
            if worker.config.enabled:
                worker.start()
        if not self._scheduler or not self._scheduler.is_alive():
            self._scheduler = threading.Thread(target=self._schedule_loop, name="phase8-scheduler", daemon=True)
            self._scheduler.start()

    def stop(self) -> None:
        self._running = False
        self._stop.set()
        for worker in list(self.workers.values()):
            worker.stop()
        if self._scheduler:
            self._scheduler.join(timeout=2)

    def start_camera(self, camera_id: str) -> dict[str, Any]:
        worker = self._get(camera_id)
        worker.start()
        return worker.health.as_dict()

    def stop_camera(self, camera_id: str) -> dict[str, Any]:
        worker = self._get(camera_id)
        worker.stop()
        return worker.health.as_dict()

    def restart_camera(self, camera_id: str) -> dict[str, Any]:
        self.stop_camera(camera_id)
        return self.start_camera(camera_id)

    def health(self, camera_id: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        values = [self._health(worker) for worker in self.workers.values()]
        if camera_id:
            return self._health(self._get(camera_id))
        return values

    def metrics(self) -> dict[str, Any]:
        return {item["camera_id"]: item for item in self.health()}

    def camera_configs(self) -> list[CameraConfig]:
        with self._registry_lock:
            return [self.workers[camera_id].config for camera_id in self._order]

    def add_camera(self, camera: CameraConfig) -> dict[str, Any]:
        with self._registry_lock:
            if camera.id in self.workers:
                raise ValueError("camera already exists")
            worker = Phase8CameraWorker(camera)
            self.workers[camera.id] = worker
            self.processors[camera.id] = self._processor_factory(camera)
            self._order.append(camera.id)
            self._processed_times[camera.id] = deque()
            self._decoded_times[camera.id] = deque()
            if self._running and camera.enabled:
                worker.start()
            return worker.health.as_dict()

    def replace_camera(self, camera_id: str, camera: CameraConfig) -> dict[str, Any]:
        if camera.id != camera_id:
            raise ValueError("camera id cannot be changed")
        with self._registry_lock:
            old = self._get(camera_id)
            old.stop()
            worker = Phase8CameraWorker(camera)
            self.workers[camera_id] = worker
            self.processors[camera_id] = self._processor_factory(camera)
            self._processed_times[camera_id].clear()
            self._decoded_times[camera_id].clear()
            self._last_processed.pop(camera_id, None)
            if self._running and camera.enabled:
                worker.start()
            return worker.health.as_dict()

    def update_camera(self, camera_id: str, values: dict[str, Any]) -> dict[str, Any]:
        worker = self._get(camera_id)
        if "enabled" in values:
            worker.config = replace(worker.config, enabled=bool(values["enabled"]))
            worker.health.enabled = worker.config.enabled
        sampling = values.get("sampling")
        if sampling:
            allowed = {"queue_size", "process_every_n_frames", "target_fps", "drop_policy"}
            sampling_values = {key: sampling[key] for key in allowed if key in sampling}
            if "queue_size" in sampling_values and int(sampling_values["queue_size"]) < 1:
                raise ValueError("queue_size must be positive")
            if "process_every_n_frames" in sampling_values and int(sampling_values["process_every_n_frames"]) < 1:
                raise ValueError("process_every_n_frames must be positive")
            worker.config = replace(worker.config, sampling=replace(worker.config.sampling, **{
                key: sampling_values[key] for key in sampling_values
            }))
            if "queue_size" in sampling_values:
                worker.queue = LatestFrameQueue(int(sampling_values["queue_size"]))
        if not worker.config.enabled:
            worker.stop()
        elif not worker.health.running:
            worker.start()
        return worker.health.as_dict()

    def remove_camera(self, camera_id: str) -> None:
        with self._registry_lock:
            worker = self._get(camera_id)
            worker.stop()
            self.workers.pop(camera_id)
            self.processors.pop(camera_id, None)
            self._order = [item for item in self._order if item != camera_id]
            self._processed_times.pop(camera_id, None)
            self._decoded_times.pop(camera_id, None)
            self._last_processed.pop(camera_id, None)
            self._cursor = 0

    def _health(self, worker: Phase8CameraWorker) -> dict[str, Any]:
        now = time.monotonic()
        health = worker.health
        for values, field_name in ((self._decoded_times[worker.config.id], "decoded_fps"), (self._processed_times[worker.config.id], "processed_fps")):
            while values and now - values[0] > 5:
                values.popleft()
            setattr(health, field_name, round(len(values) / 5, 3))
        health.queue_depth = worker.queue.depth
        if worker.last_arrival_monotonic is not None:
            health.last_frame_age_ms = round(max(0.0, (now - worker.last_arrival_monotonic) * 1000), 3)
        return health.as_dict()

    def _schedule_loop(self) -> None:
        while not self._stop.is_set():
            processed = False
            with self._registry_lock:
                camera_ids = list(self._order)
            for _ in camera_ids:
                with self._registry_lock:
                    if not self._order:
                        break
                    camera_id = self._order[self._cursor % len(self._order)]
                    self._cursor = (self._cursor + 1) % len(self._order)
                    worker = self.workers.get(camera_id)
                    processor = self.processors.get(camera_id)
                if worker is None or processor is None:
                    break
                try:
                    packet = worker.queue.get_nowait()
                except queue.Empty:
                    continue
                processed = True
                self._decoded_times[camera_id].append(time.monotonic())
                if packet.frame_index % worker.config.sampling.process_every_n_frames:
                    worker.health.frames_dropped += 1
                    continue
                packet, out_of_order = self._timestamp_guard.apply(packet)
                previous = self._last_processed.get(camera_id)
                continuity_break = previous is not None and packet.timestamp_s - previous > self._max_gap
                if out_of_order or continuity_break:
                    packet = replace(packet, session_id=f"{packet.session_id}-boundary-{uuid.uuid4().hex[:6]}")
                    worker.health.session_id = packet.session_id
                    worker.health.reconnect_epoch += 1
                started = time.perf_counter()
                try:
                    processor(packet)
                    worker.health.frames_processed += 1
                    worker.health.last_media_timestamp = packet.timestamp_s
                    self._processed_times[camera_id].append(time.monotonic())
                    self._last_processed[camera_id] = packet.timestamp_s
                    worker.health.inference_latency_ms = round((time.perf_counter() - started) * 1000, 3)
                except Exception as exc:
                    worker.health.last_error = str(exc)
            if not processed:
                time.sleep(.005)

    def _get(self, camera_id: str) -> Phase8CameraWorker:
        if camera_id not in self.workers:
            raise KeyError(camera_id)
        return self.workers[camera_id]
