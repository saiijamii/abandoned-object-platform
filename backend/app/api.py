from pathlib import Path

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
        import json
        return json.loads(path.read_text(encoding="utf-8"))

    return app


app = create_app()
