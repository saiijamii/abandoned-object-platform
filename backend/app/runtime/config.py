import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SamplingConfig:
    queue_size: int = 3
    process_every_n_frames: int = 1
    target_fps: float | None = None
    drop_policy: str = "drop_oldest"


@dataclass(frozen=True)
class ReconnectConfig:
    initial_seconds: float = 1.0
    maximum_seconds: float = 30.0
    multiplier: float = 2.0
    jitter_seconds: float = 0.25
    jitter_fraction: float = 0.20


@dataclass(frozen=True)
class CameraConfig:
    id: str
    enabled: bool
    source_kind: str
    source_uri: str | None
    secret_env: str | None = None
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    reconnect: ReconnectConfig = field(default_factory=ReconnectConfig)


def _camera(raw: dict[str, Any]) -> CameraConfig:
    source = raw.get("source", {})
    sampling = raw.get("sampling", {})
    reconnect = raw.get("reconnect", {})
    return CameraConfig(
        id=str(raw["id"]),
        enabled=bool(raw.get("enabled", True)),
        source_kind=str(source.get("kind", "fake")),
        source_uri=source.get("uri"),
        secret_env=source.get("secret_env"),
        sampling=SamplingConfig(
            queue_size=max(1, int(sampling.get("queue_size", 3))),
            process_every_n_frames=max(1, int(sampling.get("process_every_n_frames", 1))),
            target_fps=float(sampling["target_fps"]) if sampling.get("target_fps") is not None else None,
            drop_policy=str(sampling.get("drop_policy", "drop_oldest")),
        ),
        reconnect=ReconnectConfig(**{key: reconnect[key] for key in ReconnectConfig.__dataclass_fields__ if key in reconnect}),
    )


def load_runtime_config(path: str | Path) -> tuple[dict[str, Any], list[CameraConfig]]:
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data, [_camera(item) for item in data.get("cameras", [])]


def resolve_secret(camera: CameraConfig) -> str | None:
    if camera.secret_env:
        return os.environ.get(camera.secret_env)
    return camera.source_uri


def redact_uri(uri: str | None) -> str | None:
    if not uri:
        return uri
    if "@" in uri and "://" in uri:
        prefix, suffix = uri.split("://", 1)
        _, host = suffix.rsplit("@", 1)
        return f"{prefix}://***:***@{host}"
    return uri
