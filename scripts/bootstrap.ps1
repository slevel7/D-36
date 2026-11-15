# Run from the repository root. Installs local development dependencies only.
$ErrorActionPreference = 'Stop'
python -m pip install -r apps/api/requirements.txt
if ($LASTEXITCODE) { throw 'Python dependency installation failed' }
Push-Location apps/web
try {
  npm.cmd ci
  if ($LASTEXITCODE) { throw 'Web dependency installation failed' }
} finally { Pop-Location }
Write-Host 'Set DEMO_PASSWORD, then run scripts/seed_demo.ps1. See README for startup.'
