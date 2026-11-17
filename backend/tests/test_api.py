from fastapi.testclient import TestClient

from app.api import create_app


def test_health_and_empty_runs(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/v1/health").json() == {"status": "ok", "phase": "one"}
    assert client.get("/api/v1/runs").json() == []
    assert client.get("/api/events").json() == []
