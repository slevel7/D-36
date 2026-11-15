# Windows 11 developer and operator guide

This is an existing repository recovery. Do not initialize a new repository, reset history or overwrite local work. From an existing checkout use the current feature branch after inspecting `git status` and `git branch -vv`. A new machine may clone `https://github.com/slevel7/D-36.git`, then switch to `feat/brahmagpt-full-platform`.

## Prerequisites and setup

Python 3.13, Node 22 and Git are used in local verification. The web lockfile pins a supported TypeScript 6.0 / ESLint 10 combination. Dependencies are development dependencies unless required by the app. Install from repository root:

```powershell
./scripts/bootstrap.ps1
$env:DEMO_PASSWORD = 'Choose-a-unique-local-demo-password'
./scripts/seed_demo.ps1
```

`seed_demo.ps1` runs Alembic then seeds fictional users. Seeding does not reset existing passwords. The default SQLite file is anchored to apps/api/brahma.db, independently of terminal working directory. Existing pre-Alembic demo data was backed up and adopted once during recovery; do not blindly stamp another database. Fresh clones use `alembic upgrade head` normally.

Run the password-free local preview API in one terminal:

```powershell
./scripts/start_demo.ps1
```

This enables explicit development-only employee entry. To require passwords, start normally instead:

```powershell
python -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
Set-Location apps/web
npm.cmd ci
npm.cmd run dev -- --hostname 127.0.0.1
```

Open http://localhost:3000. API documentation is http://127.0.0.1:8000/docs. Local demo users: employee@example.test, reviewer@example.test, admin@example.test, other@example.test. Their password is your own DEMO_PASSWORD from first seeding. No public registration exists. For a human review session, open /login in a separate browser profile or sign out and use the reviewer account. Automatic employee entry is not used on /login.

Linux/macOS: use `export DEMO_PASSWORD='...'`; use npm instead of npm.cmd. From apps/api run `python -m alembic upgrade head`, `python seed_demo.py`, and `python -m uvicorn main:app --host 127.0.0.1 --port 8000`. To use automatic demo entry explicitly set APP_ENV=development and DEMO_AUTO_LOGIN=true.

## Docker Desktop and PostgreSQL

Docker was not found on PATH or the inspected standard installation paths on the implementation machine. No local Docker success is claimed. Check your own installation:

```powershell
Get-Command docker -ErrorAction SilentlyContinue
Test-Path 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
Get-ChildItem "$env:LOCALAPPDATA\Programs" -Filter docker.exe -File -Recurse -ErrorAction SilentlyContinue
```

If Docker exists, add its containing bin folder to your user PATH, restart VS Code/terminals, start Docker Desktop with its WSL2 engine, then run `docker version`, `docker info` and `docker compose version`. A CLI file alone does not mean the engine is running.

Copy .env.example to .env and fill unique local PostgreSQL/MinIO secrets. Never commit .env. Then run `docker compose up -d` and `docker compose ps`. Export DATABASE_URL to the API terminal (Compose .env is not automatically imported by Python), stop the SQLite API, run migrations and seed against the intended PostgreSQL database, then restart. Verify with `python -m alembic -c apps/api/alembic.ini current` and `check`. Redis/MinIO services are configured but application worker/object-storage integration remains unfinished.

## Verification

```powershell
python -m pytest -q
python -m ruff check apps/api scripts
python scripts/check_secrets.py
Set-Location apps/web
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
$env:E2E_PASSWORD = 'Your-existing-local-seed-password'
npm.cmd run test:e2e
npm.cmd audit
```

Run browser tests against started local API/web services. They create only synthetic demo data. E2E_PASSWORD must match the existing reviewer/admin seed accounts; changing the environment variable does not reset a previously seeded password. Source fixtures are under apps/web/e2e/fixtures. Captures are under docs/screenshots. REFERENCE_COMPARISON.html places the supplied reference next to current captures. No screenshot-perfect equivalence is claimed.

CI is configured for API/lint, web checks, PostgreSQL migrations and browser flows. Its result is independent of local checks and must be read from GitHub Actions. Full Docker Compose/worker operation and automated image-diff baselines are not proven by those jobs.

## Operation and troubleshooting

Use the nine Profile sections for actual settings/requests and the six Customize tabs for catalogue/favourites/history. Projects provide membership, linked tasks/files, meetings, discussions and archival. Pension and grievances have separate illustrative workflows; no official sanction is implied. Documents preserves original bytes and offers extracted source citations, draft versions, recommendations, human review and review-copy exports. Outreach uses only a simulator.

If a port is occupied, identify the process before stopping it; never kill unrelated apps. If sign-in returns 429, the form/API returns a retry window after failed attempts. If credentials fail, verify the original seed password and account email; do not disable authentication in production. If schema errors occur, stop the API, back up the database and run migrations against the intended DATABASE_URL. If an external provider says Not configured, it cannot send, sync or create external meeting URLs. Real OAuth, hosted AI and government connections need additional implementation and approved credentials; supplying a key alone does not make the current catalogue functional.

No production deployment should be attempted before the remaining acceptance failures, granular classification policies, TLS/secret management, security review, operational backups/restore and departmental authorisation are addressed. Real data must not enter this public source repository.

## Existing GitHub delivery

Use `git status`, review changes and run checks. Commit to the existing feature branch, then `git push origin feat/brahmagpt-full-platform`. Update PR #1 into main. Never force push, create another repository or self-merge. Temporary test-service passwords in CI apply only to ephemeral synthetic databases; they are not production credentials.
