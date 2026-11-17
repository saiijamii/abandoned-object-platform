# Phase 8

Phase 8 adds multi-camera runtime scaling around existing Phase 5 processing.

Run checks:

```powershell
python -m pip install -r backend/requirements-phase8.txt
.\scripts\test_phase8.ps1
```

Set RTSP URLs through `secret_env`. Do not place credentials in YAML or API payloads.
Use `backend/config/phase8.example.yaml` as starting config.
