# D-36

BrahmaGPT by Singularity: an internal employee workspace. **Incremental build, not production ready.** All demonstration records are fictional. This repository preserves the original D-36 history.

## Local setup (Windows 11 PowerShell)

Prerequisites: Python 3.13, Node 22+, Git. Docker Desktop with WSL2 is optional for the currently available SQLite development path, required for PostgreSQL services.

```powershell
python -m pip install -r apps/api/requirements.txt
$env:DEMO_PASSWORD = 'Choose-your-local-demo-password'
Set-Location apps/api
python -m alembic upgrade head
python seed_demo.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second terminal at repository root:

```powershell
Set-Location apps/web
npm.cmd ci
npm.cmd run dev
```

Web: http://localhost:3000 · API documentation: http://127.0.0.1:8000/docs. These are expected startup URLs, not a hosted deployment.

Synthetic accounts use your chosen `DEMO_PASSWORD`: `employee@example.test` (employee), `reviewer@example.test` (reviewer), `admin@example.test` (platform admin; separate administration department), `other@example.test` (separate department). No public registration. Demo passwords are not shipped or embedded in the frontend.

Linux/macOS: use `export DEMO_PASSWORD='...'`, `cd` instead of `Set-Location`, and `npm` instead of `npm.cmd`. Run the same Python commands.

## PostgreSQL services

Copy `.env.example` to `.env`, supply strong local service secrets, start Docker Desktop, then `docker compose up -d`. Export `DATABASE_URL` into the API terminal before running the schema bootstrap. Compose reads `.env`; Python requires environment variables explicitly. Run the initial migration on a fresh development database; An initial Alembic migration is verified on SQLite; PostgreSQL execution remains unverified. Redis and MinIO are provisioned only and not integrated with application jobs or uploads. Docker was unavailable on the implementation host; this path has not been executed.

## Verify

```powershell
python -m pytest -q
Set-Location apps/web
npm.cmd run typecheck
npm.cmd run build
```

Current scope: session authentication, department-scoped basic records, immutable text sources and draft revisions, deterministic grounded draft compilation, exact paragraph evidence, separate-human review decisions and real DOCX/PDF review exports. Full specification is [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md); honest coverage is [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md).

The supplied reference and lotus were subsequently uploaded, inspected and preserved in reference/ and assets/. The application uses the supplied monochrome SVG geometry. Hosted AI and external integrations remain unconfigured; see docs/STATUS.md for current scope.

See [walkthrough](docs/WALKTHROUGH.md), [security](docs/SECURITY.md), [limitations](docs/KNOWN_LIMITATIONS.md), and [status](docs/STATUS.md).

## Skip login for the local demo

With the existing demo database seeded, start the API using `./scripts/start_demo.ps1`, and start the web app normally. This sets APP_ENV=development and DEMO_AUTO_LOGIN=true only for the local API process. Opening the web page automatically creates a demo employee session; no password entry is required. Normal authentication remains the default when these flags are absent. Do not enable this option for real data or a publicly exposed environment. Stop this API and restart without DEMO_AUTO_LOGIN to restore password entry.

## Corrective recovery

Profile: /profile; Customize: /customize; supplied lotus and inspected reference anatomy in grayscale. Existing UI is retained at /legacy during domain replacement. See docs/RECOVERY_GAP_AUDIT.md, docs/ACCEPTANCE_MATRIX.md and docs/UX_SPEC.md. Backend: `python -m pytest -q`. From apps/web: `npx playwright test e2e/recovery.spec.ts`; set E2E_PASSWORD to the local seeded password for `npx playwright test e2e/documents.spec.ts` with a separate reviewer. No local password is embedded in browser tests.

The latest local recovery verification is 17 API tests and 8 browser scenarios, plus lint, typecheck, build, SQLite migration checks and a zero-finding dependency audit. This is not full acceptance completion. Start with [Windows setup](docs/WINDOWS_SETUP.md), [acceptance results](docs/ACCEPTANCE_MATRIX.md), [current status](docs/STATUS.md) and [reference comparison](docs/REFERENCE_COMPARISON.html).
