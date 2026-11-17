import os

import pytest


security = pytest.importorskip("app.phase9.security")
evidence = pytest.importorskip("app.phase9.evidence")


def test_password_and_token_round_trip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    encoded = security.password_hash("secret")
    assert security.password_matches("secret", encoded)
    assert not security.password_matches("wrong", encoded)
    token = security.issue_token("operator", "operator")
    assert security.decode_token(token)["sub"] == "operator"


def test_redaction_hides_credentials():
    value = security.redact_text("rtsp://alice:secret@example.test/live bearer abc123")
    assert "secret" not in value
    assert "abc123" not in value
    assert "***" in value


def test_evidence_hash_and_path_safety(tmp_path):
    store = evidence.EvidenceStore(tmp_path)
    result = store.write("event-1", "frame.jpg", b"image", "image/jpeg")
    assert result["byte_size"] == 5
    assert result["sha256"]
    with pytest.raises(ValueError):
        store.write("event-1", "..\\secret.txt", b"x", "image/jpeg")
