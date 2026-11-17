from pathlib import Path
from typing import Any

from ..api import create_app
from .config import load_runtime_config
from .processor import passthrough_factory
from .worker import CameraManager


def create_runtime_app(config_path: str | Path, storage_root: str | Path = "storage"):
    config, cameras = load_runtime_config(config_path)
    manager = CameraManager(cameras, passthrough_factory)
    return create_app(storage_root, manager, cameras)
