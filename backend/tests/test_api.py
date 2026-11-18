from fastapi.testclient import TestClient
import yaml

from app.api import create_app


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
    saved = client.put("/api/config", json={"runtime": {"max_continuity_gap_seconds": 2}, "cameras": [{"id": "cam", "enabled": False, "sampling": {"queue_size": 3}}]})
    assert saved.status_code == 200
    assert "secret" not in saved.text
    persisted = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert persisted["runtime"]["max_continuity_gap_seconds"] == 2
    assert persisted["cameras"][0]["enabled"] is False
    invalid = client.put("/api/config", json={"runtime": {"max_continuity_gap_seconds": -1}})
    assert invalid.status_code == 400
    invalid_camera = client.put("/api/config", json={"cameras": [{"id": "cam", "sampling": {"queue_size": 0}}]})
    assert invalid_camera.status_code == 400
