from pathlib import Path
import json
import copy
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .runtime.config import redact_uri
from .runtime.worker import CameraManager


def create_app(storage_root: str | Path = "storage", manager: CameraManager | None = None, camera_configs: list | None = None, config_path: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app):
        try:
            from .phase9.persistence import recover_running_sessions
            recover_running_sessions()
        except Exception:
            pass
        if manager:
            manager.start()
        try:
            yield
        finally:
            if manager:
                manager.stop()

    app = FastAPI(title="Abandoned Object Platform", version="0.1.0", lifespan=lifespan)
    root = Path(storage_root)
    try:
        from .search.routes import router as search_router
        app.include_router(search_router)
    except (ImportError, RuntimeError):
        pass
    try:
        from .phase9.routes import router as phase9_router
        app.include_router(phase9_router)
    except ImportError:
        pass

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

    @app.get("/api/events")
    def runtime_events() -> list[dict]:
        return events()

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
        return _public_config(yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {})

    @app.put("/api/config")
    def update_config(value: dict) -> dict:
        if not config_path:
            raise HTTPException(status_code=503, detail="config file is not configured")
        import yaml
        path = Path(config_path)
        current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key in ("runtime", "ownership", "alerts", "alert"):
            if key in value:
                _validate_settings(key, value[key])
                current[key] = value[key]
        configured = {camera.get("id"): camera for camera in current.get("cameras", [])}
        for camera in value.get("cameras", []):
            if camera.get("id") not in configured:
                raise HTTPException(status_code=400, detail=f"unknown camera: {camera.get('id')}")
            source = camera.get("source", {})
            if source.get("uri") or source.get("password"):
                raise HTTPException(status_code=400, detail="source secrets must use secret_env")
            _validate_camera_settings(camera)
            if "enabled" in camera:
                camera["enabled"] = bool(camera["enabled"])
            if "sampling" in camera:
                camera["sampling"] = {**camera["sampling"]}
                for key in ("queue_size", "process_every_n_frames"):
                    if key in camera["sampling"]:
                        camera["sampling"][key] = int(camera["sampling"][key])
            target = configured[camera["id"]]
            for key in ("enabled", "sampling", "reconnect"):
                if key in camera:
                    target[key] = camera[key]
            if manager and hasattr(manager, "update_camera"):
                manager.update_camera(camera["id"], {key: camera[key] for key in ("enabled", "sampling") if key in camera})
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
        temporary.replace(path)
        return _public_config(current)

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
            values.append({"id": camera.id, "enabled": camera.enabled, "source_kind": camera.source_kind, "secret_env": camera.secret_env, "source_uri": redact_uri(camera.source_uri) if not camera.secret_env else None})
        return values

    @app.get("/api/cameras/{camera_id}/health")
    def camera_health(camera_id: str) -> dict:
        if not manager:
            raise HTTPException(status_code=503, detail="camera manager is not configured")
        try:
            return manager.health(camera_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="camera not found")

    @app.get("/api/phase8/cameras")
    def phase8_cameras() -> list[dict]:
        if not manager:
            return []
        return manager.health()

    @app.put("/api/phase8/cameras/{camera_id}")
    def update_phase8_camera(camera_id: str, value: dict) -> dict:
        if not manager or not hasattr(manager, "update_camera"):
            raise HTTPException(status_code=503, detail="phase 8 manager is not configured")
        if any(key in value for key in ("source", "uri", "password", "secret_env")):
            raise HTTPException(status_code=400, detail="source secrets cannot be changed through this API")
        try:
            return manager.update_camera(camera_id, value)
        except KeyError:
            raise HTTPException(status_code=404, detail="camera not found")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.delete("/api/phase8/cameras/{camera_id}")
    def delete_phase8_camera(camera_id: str) -> dict[str, str]:
        if not manager or not hasattr(manager, "remove_camera"):
            raise HTTPException(status_code=503, detail="phase 8 manager is not configured")
        try:
            manager.remove_camera(camera_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="camera not found")
        return {"camera_id": camera_id, "status": "removed"}

    @app.get("/api/phase8/metrics")
    def phase8_metrics() -> dict:
        return manager.metrics() if manager and hasattr(manager, "metrics") else {}

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
            lines.append(f'camera_queue_depth{{camera_id="{label}"}} {item.get("queue_depth", 0)}')
            lines.append(f'camera_decoded_fps{{camera_id="{label}"}} {item.get("decoded_fps", 0)}')
            lines.append(f'camera_processed_fps{{camera_id="{label}"}} {item.get("processed_fps", 0)}')
        return "\n".join(lines) + "\n"

    return app


def _validate_settings(section: str, value: dict) -> None:
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail=f"{section} must be an object")
    numeric = {
        "runtime": {"max_continuity_gap_seconds"},
        "ownership": {"association_seconds", "association_max_distance_ratio", "separation_distance_ratio", "ambiguous_owner_margin_ratio"},
        "alerts": {"separation_seconds", "stationary_window_seconds", "stationary_max_movement_ratio", "min_stationary_observations"},
        "alert": {"separation_seconds", "stationary_window_seconds", "stationary_max_movement_ratio", "min_stationary_observations"},
    }[section]
    for key in numeric:
        if key in value:
            try:
                if float(value[key]) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"{section}.{key} must be non-negative")


def _validate_camera_settings(camera: dict) -> None:
    sampling = camera.get("sampling", {})
    if not isinstance(sampling, dict):
        raise HTTPException(status_code=400, detail="camera sampling must be an object")
    for key in ("queue_size", "process_every_n_frames"):
        if key in sampling:
            try:
                if int(sampling[key]) < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"camera sampling {key} must be positive")
    if "drop_policy" in sampling and sampling["drop_policy"] not in {"drop_oldest", "drop_newest"}:
        raise HTTPException(status_code=400, detail="camera sampling drop_policy is invalid")


def _public_config(value: dict) -> dict:
    public = copy.deepcopy(value)
    for camera in public.get("cameras", []):
        source = camera.get("source", {})
        source.pop("password", None)
        if source.get("secret_env"):
            source.pop("uri", None)
        elif source.get("uri"):
            source["uri"] = redact_uri(source["uri"])
    return public


app = create_app()


def _collection(root: Path, name: str) -> list[dict]:
    directory = root / "cameras" if name == "events" else root / name
    if not directory.exists():
        return []
    paths = directory.rglob("metadata.json") if name == "events" else directory.rglob("*.json")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paths)]


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []
