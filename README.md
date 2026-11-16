# Abandoned Object Platform

Phase One prototype: normalize person/luggage detection, measure quality, and prepare annotated video output.

Phase Two adds optional BoxMOT tracking, temporal owner association, source-time separation events, evidence snapshots, and read-only event/track APIs.

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

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Research and visual references remain outside this checkout. Phase Two accepts no event when detector emits no luggage track.
