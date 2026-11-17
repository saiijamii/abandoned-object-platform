from pathlib import Path
from typing import Any

from ..api import create_app
from .config import load_runtime_config
from .phase5 import phase5_factory
from .phase8 import Phase8CameraManager


def create_runtime_app(config_path: str | Path, storage_root: str | Path = "storage"):
    config, cameras = load_runtime_config(config_path)
    manager = Phase8CameraManager(cameras, phase5_factory(config, str(storage_root)), storage_root, config.get("runtime", {}))
    return create_app(storage_root, manager, cameras, config_path)
