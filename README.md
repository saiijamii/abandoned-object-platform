# Abandoned Object Platform

Phase One prototype: normalize person/luggage detection, measure quality, and prepare annotated video output.

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

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Research and visual references remain outside this checkout. Phase Two stays out of scope until detector recall passes the project gate.
