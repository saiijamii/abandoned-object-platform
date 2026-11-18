# Phase 10 release-candidate validation

Current platform is Phase 8/9 runtime. Phase 10 validates current platform with deterministic fake-camera tests.

Run backend tests, phase10-smoke.ps1, phase10-failure-drills.ps1, phase10-benchmark.ps1, and frontend build.

Compose waits for PostgreSQL health before starting backend.

Current gates:

- Fake-camera smoke: locally runnable.
- Queue bound: measured by smoke test.
- Reconnect drill: deterministic fake source.
- PostgreSQL migration and restore: requires Docker/PostgreSQL.
- Real MP4 baseline: unavailable until sample MP4 exists.
- Real RTSP reconnect: unavailable until RTSP test source exists.
- GPU benchmark: unavailable until GPU runtime exists.
- Production readiness: not claimed.
