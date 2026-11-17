from pathlib import Path
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .runtime.config import redact_uri
from .runtime.worker import CameraManager


def create_app(storage_root: str | Path = "storage", manager: CameraManager | None = None, camera_configs: list | None = None, config_path: str | Path | None = None) -> FastAPI:
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

    @app.get("/api/config")
    def config() -> dict:
        if not config_path or not Path(config_path).is_file():
            return {}
        import yaml
        value = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        for camera in value.get("cameras", []):
            source = camera.get("source", {})
            if source.get("secret_env"):
                source.pop("uri", None)
        return value

    @app.put("/api/config")
    def update_config(value: dict) -> dict:
        if not config_path:
            raise HTTPException(status_code=503, detail="config file is not configured")
        import yaml
        path = Path(config_path)
        current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key in ("runtime", "ownership", "alerts", "alert"):
            if key in value:
                current[key] = value[key]
        for camera in value.get("cameras", []):
            source = camera.get("source", {})
            if source.get("uri") or source.get("password"):
                raise HTTPException(status_code=400, detail="source secrets must use secret_env")
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
        temporary.replace(path)
        return current

    @app.get("/api/tracks/{camera_id}/{session_id}")
    def camera_tracks(camera_id: str, session_id: str) -> dict:
        base = root / "cameras" / camera_id / "sessions" / session_id
        return {"tracks": _jsonl(base / "tracks.jsonl"), "associations": _jsonl(base / "associations.jsonl")}

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
    directory = root / "cameras" if name == "events" else root / name
    if not directory.exists():
        return []
    paths = directory.rglob("metadata.json") if name == "events" else directory.rglob("*.json")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paths)]


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []
