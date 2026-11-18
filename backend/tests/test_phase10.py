from app.phase10 import run_reconnect_drill, run_smoke


def test_phase10_smoke_keeps_camera_state_separate() -> None:
    result = run_smoke(camera_count=2, frames=8, queue_size=2)
    assert result.status == "pass"
    assert result.camera_count == 2
    assert result.frames_read == 16
    assert result.max_queue_depth <= 2


def test_phase10_reconnect_drill_recovers_after_source_failure() -> None:
    result = run_reconnect_drill()
    assert result["status"] == "pass"
