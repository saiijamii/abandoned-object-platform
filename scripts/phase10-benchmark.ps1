param([int]$Cameras = 2, [int]$Frames = 300)
$ErrorActionPreference = "Stop"
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
$env:PYTHONPATH = "$PWD\backend"
& $python -c "import json; from app.phase10 import run_smoke; print(json.dumps(run_smoke($Cameras, $Frames).as_dict(), indent=2))"
if ($LASTEXITCODE -ne 0) { throw "Phase 10 benchmark failed" }
