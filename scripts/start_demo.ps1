# Local fictional-data preview only. Existing seeded database required.
$ErrorActionPreference = 'Stop'
$env:APP_ENV = 'development'
$env:DEMO_AUTO_LOGIN = 'true'
Push-Location (Join-Path $PSScriptRoot '../apps/api')
try {
    python -m uvicorn main:app --host 127.0.0.1 --port 8000
} finally { Pop-Location }
