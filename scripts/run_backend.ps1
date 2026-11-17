param(
  [string]$Config = ".\backend\config\phase4.example.yaml",
  [int]$Port = 8000
)

$env:PHASE4_CONFIG = $Config
$env:PYTHONPATH = ".\backend"
python -m uvicorn app.runtime.main:app --host 127.0.0.1 --port $Port
