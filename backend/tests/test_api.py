from fastapi.testclient import TestClient
import yaml

from app.api import create_app
from app.runtime.phase8 import Phase8CameraManager


def test_health_and_empty_runs(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/v1/health").json() == {"status": "ok", "phase": "one"}
    assert client.get("/api/v1/runs").json() == []
    assert client.get("/api/events").json() == []


def test_config_redacts_sources_and_persists_supported_settings(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"runtime": {"max_continuity_gap_seconds": 1}, "cameras": [{"id": "cam", "enabled": True, "source": {"kind": "rtsp", "uri": "rtsp://user:secret@example.test/live"}, "sampling": {"queue_size": 2}}]}), encoding="utf-8")
    client = TestClient(create_app(tmp_path, config_path=config_path))
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "secret" not in response.text
    saved = client.put("/api/config", json={"runtime": {"max_continuity_gap_seconds": "2"}, "cameras": [{"id": "cam", "enabled": False, "sampling": {"queue_size": 3}}]})
    assert saved.status_code == 200
    assert "secret" not in saved.text
    persisted = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert persisted["runtime"]["max_continuity_gap_seconds"] == 2.0
    assert persisted["cameras"][0]["enabled"] is False
    invalid = client.put("/api/config", json={"runtime": {"max_continuity_gap_seconds": -1}})
    assert invalid.status_code == 400
    invalid_camera = client.put("/api/config", json={"cameras": [{"id": "cam", "sampling": {"queue_size": 0}}]})
    assert invalid_camera.status_code == 400


def test_camera_crud_persists_registry_and_rejects_credentials(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("cameras: []\n", encoding="utf-8")
    manager = Phase8CameraManager([], lambda camera: lambda packet: None)
    client = TestClient(create_app(tmp_path, manager, [], config_path))
    created = client.post("/api/cameras", json={"id": "cam", "enabled": False, "source": {"kind": "fake"}, "sampling": {"queue_size": 2}})
    assert created.status_code == 201
    assert client.get("/api/cameras").json()[0]["id"] == "cam"
    updated = client.put("/api/cameras/cam", json={"enabled": False, "source": {"kind": "http", "uri": "http://example.test/live"}, "sampling": {"queue_size": 3}})
    assert updated.status_code == 200
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["cameras"][0]["source"]["kind"] == "http"
    rejected = client.post("/api/cameras", json={"id": "bad", "source": {"kind": "rtsp", "uri": "rtsp://user:password@example.test/live"}})
    assert rejected.status_code == 400
    monkeypatch.setattr("app.api.test_source", lambda camera: {"ok": True, "width": 640, "height": 480, "latency_ms": 1})
    assert client.post("/api/cameras/test", json={"id": "test", "source": {"kind": "http", "uri": "http://example.test/live"}}).json()["ok"] is True
    assert client.delete("/api/cameras/cam").status_code == 200
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["cameras"] == []
