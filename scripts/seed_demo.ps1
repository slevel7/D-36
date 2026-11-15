$ErrorActionPreference = 'Stop'
if (-not $env:DEMO_PASSWORD) { throw 'Set DEMO_PASSWORD first (at least 12 characters).' }
Push-Location apps/api
try {
  python -m alembic upgrade head
  if ($LASTEXITCODE) { throw 'Migration failed' }
  python seed_demo.py
  if ($LASTEXITCODE) { throw 'Seed failed' }
} finally { Pop-Location }
