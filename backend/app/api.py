from pathlib import Path
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .runtime.config import redact_uri
from .runtime.processor import passthrough_factory
from .runtime.worker import CameraManager


def create_app(storage_root: str | Path = "storage", manager: CameraManager | None = None, camera_configs: list | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app):
        if manager:
            manager.start()
        try:
            yield
        finally:
            if manager:
                manager.stop()

    app = FastAPI(title="Abandoned Object Platform", version="0.1.0", lifespan=lifespan)
    root = Path(storage_root)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "phase": "one"}

    @app.get("/api/v1/runs")
    def runs() -> list[dict]:
        return [
            {"id": path.stem, "name": path.stem, "status": "complete"}
            for path in sorted((root / "runs").glob("*.json"))
        ] if (root / "runs").exists() else []

    @app.get("/api/v1/runs/{run_id}")
    def run(run_id: str) -> dict:
        path = root / "runs" / f"{run_id}.json"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="run not found")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/api/v1/events")
    def events() -> list[dict]:
        return _collection(root, "events")

    @app.get("/api/v1/events/{event_id}")
    def event(event_id: str) -> dict:
        value = next((item for item in _collection(root, "events") if item.get("event_id") == event_id), None)
        if value is None:
            raise HTTPException(status_code=404, detail="event not found")
        return value

    @app.get("/api/v1/tracks")
    def tracks() -> list[dict]:
        return _collection(root, "tracks")

    @app.get("/api/health")
    def runtime_health() -> dict:
        return {"status": "ok", "cameras": manager.health() if manager else []}

    @app.get("/api/cameras")
    def cameras() -> list[dict]:
        values = []
        for camera in camera_configs or []:
            values.append({"id": camera.id, "enabled": camera.enabled, "source_kind": camera.source_kind, "source_uri": redact_uri(camera.source_uri) if not camera.secret_env else None})
        return values

    @app.get("/api/cameras/{camera_id}/health")
    def camera_health(camera_id: str) -> dict:
        if not manager:
            raise HTTPException(status_code=503, detail="camera manager is not configured")
        try:
            return manager.health(camera_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="camera not found")

    def camera_action(camera_id: str, action: str) -> dict:
        if not manager:
            raise HTTPException(status_code=503, detail="camera manager is not configured")
        try:
            return getattr(manager, f"{action}_camera")(camera_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="camera not found")

    @app.post("/api/cameras/{camera_id}/start")
    def start_camera(camera_id: str) -> dict:
        return camera_action(camera_id, "start")

    @app.post("/api/cameras/{camera_id}/stop")
    def stop_camera(camera_id: str) -> dict:
        return camera_action(camera_id, "stop")

    @app.post("/api/cameras/{camera_id}/restart")
    def restart_camera(camera_id: str) -> dict:
        return camera_action(camera_id, "restart")

    @app.get("/api/search/capabilities")
    def search_capabilities() -> dict:
        return {"person": False, "luggage": False, "status": "reserved"}

    @app.get("/metrics")
    def metrics() -> str:
        health = manager.health() if manager else []
        lines = ["# TYPE camera_frames_read counter"]
        for item in health:
            label = item["camera_id"]
            lines.append(f'camera_frames_read{{camera_id="{label}"}} {item["frames_read"]}')
            lines.append(f'camera_frames_processed{{camera_id="{label}"}} {item["frames_processed"]}')
            lines.append(f'camera_frames_dropped{{camera_id="{label}"}} {item["frames_dropped"]}')
        return "\n".join(lines) + "\n"

    return app


app = create_app()


def _collection(root: Path, name: str) -> list[dict]:
    directory = root / name
    if not directory.exists():
        return []
    paths = directory.rglob("metadata.json") if name == "events" else directory.rglob("*.json")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paths)]
