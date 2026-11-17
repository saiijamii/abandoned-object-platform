# Abandoned Object Platform

Phase One prototype: normalize person/luggage detection, measure quality, and prepare annotated video output.

Phase Two adds optional BoxMOT tracking, temporal owner association, source-time separation events, evidence snapshots, and read-only event/track APIs.

Phase Three connects detector, tracker, ownership, event, and evidence paths against a real MP4.

## Backend

```powershell
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements-dev.txt
python -m pytest backend/tests -q
uvicorn app.main:app --app-dir backend --reload
```

Optional model adapters:

```powershell
.venv\Scripts\pip install -r backend\requirements-optional.txt
```

Phase Two tracker:

```powershell
.venv\Scripts\pip install -r backend\requirements-phase2.txt
python scripts\run_synthetic_demo.py
```

Phase Three run:

```powershell
.venv\Scripts\pip install -r backend\requirements-phase3.txt
python scripts\run_phase3.py `
  --input .\data\videos\sample.mp4 `
  --output .\storage\runs\phase3_annotated.mp4 `
  --config .\backend\config\phase3.yaml `
  --camera-id camera_01 `
  --session-id sample_mp4_run_001 `
  --metrics .\storage\runs\phase3_metrics.json
```

Detection frame rate is not recall. Evaluate annotated CSV boxes with `scripts\evaluate_recall.py`.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Research and visual references remain outside this checkout. Phase Two accepts no event when detector emits no luggage track.
