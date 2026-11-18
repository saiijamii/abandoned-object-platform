import os
from pathlib import Path

from .app_factory import create_runtime_app

default_config = Path(__file__).resolve().parents[2] / "config" / "phase5.example.yaml"
config_path = Path(os.environ.get("PHASE4_CONFIG", default_config))
app = create_runtime_app(config_path)
