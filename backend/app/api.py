from pathlib import Path
import json

from fastapi import FastAPI, HTTPException


def create_app(storage_root: str | Path = "storage") -> FastAPI:
    app = FastAPI(title="Abandoned Object Platform", version="0.1.0")
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

    return app


app = create_app()


def _collection(root: Path, name: str) -> list[dict]:
    directory = root / name
    if not directory.exists():
        return []
    paths = directory.rglob("metadata.json") if name == "events" else directory.rglob("*.json")
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paths)]
