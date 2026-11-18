$ErrorActionPreference = "Stop"
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
$env:PYTHONPATH = "$PWD\backend"
& $python -c "import json; from app.phase10 import run_reconnect_drill; print(json.dumps(run_reconnect_drill(), indent=2))"
if ($LASTEXITCODE -ne 0) { throw "Phase 10 failure drill failed" }
