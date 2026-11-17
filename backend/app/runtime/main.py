import os
from pathlib import Path

from ..api import app as default_app
from .app_factory import create_runtime_app

config_path = os.environ.get("PHASE4_CONFIG")
app = create_runtime_app(config_path) if config_path and Path(config_path).exists() else default_app
