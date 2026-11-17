# Phase 9 checkpoint

Phase 9 adds an additive security and persistence foundation.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-phase9.txt
docker compose -f .\docker-compose.phase9.yml up -d postgres
$env:DATABASE_URL = "postgresql+psycopg://app:app@localhost:5432/abandoned_luggage"
$env:JWT_SECRET = "replace-with-at-least-32-random-characters"
$env:PYTHONPATH = "$PWD\backend"
Push-Location backend
python -m alembic -c .\alembic.ini upgrade head
python .\scripts\create_phase9_user.py admin "replace-with-a-long-password"
Pop-Location
python -m uvicorn app.main:app --app-dir backend --reload
```

Endpoints:

- `GET /health/live` checks process health.
- `GET /health/ready` checks PostgreSQL.
- `POST /auth/token` accepts JSON username and password.
- `GET /auth/me` validates bearer JWT.
- `POST /api/phase9/events` uses database idempotency.
- `POST /api/phase9/evidence` accepts authenticated JPEG, PNG, or WebP uploads.

Existing Phase 8 JSON and SQLite APIs remain available. PostgreSQL migration of those stores is not automatic.
