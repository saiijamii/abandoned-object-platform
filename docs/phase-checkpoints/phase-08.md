# Phase 8 checkpoint: real RTSP and multi-camera scale

Implemented:

- Per-camera readers with bounded latest-frame queues.
- Shared fair round-robin inference scheduler.
- Media timestamp clamping and continuity session boundaries.
- RTSP reconnect backoff with jitter.
- Per-camera health and throughput metrics.
- Persistent local event dedupe ledger.
- Phase 8 camera and metrics API routes.

Not verified in this repository:

- Live RTSP decoder compatibility.
- GPU throughput, CPU/RAM limits, or two real cameras.
- Production multi-process ledger locking and authentication.
