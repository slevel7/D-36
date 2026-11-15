# D-36

BrahmaGPT by Singularity: an internal employee workspace. **Incremental build, not production ready.** All demonstration records are fictional. This repository preserves the original D-36 history.

## Local setup (Windows 11 PowerShell)

Prerequisites: Python 3.13, Node 22+, Git. Docker Desktop with WSL2 is optional for the currently available SQLite development path, required for PostgreSQL services.

```powershell
python -m pip install -r apps/api/requirements.txt
$env:DEMO_PASSWORD = 'Choose-your-local-demo-password'
Set-Location apps/api
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

Copy `.env.example` to `.env`, supply strong local service secrets, start Docker Desktop, then `docker compose up -d`. Export `DATABASE_URL` into the API terminal before running the schema bootstrap. Compose reads `.env`; Python requires environment variables explicitly. The bootstrap creates tables for a fresh development database; Alembic upgrade migrations are not yet implemented. Redis and MinIO are provisioned only and not integrated with application jobs or uploads. Docker was unavailable on the implementation host; this path has not been executed.

## Verify

```powershell
python -m pytest -q
Set-Location apps/web
npm.cmd run typecheck
npm.cmd run build
```

Current scope: session authentication, department-scoped basic records, immutable text sources and draft revisions, deterministic grounded draft compilation, exact paragraph evidence, separate-human review decisions and real DOCX/PDF review exports. Full specification is [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md); honest coverage is [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md).

The supplied lotus file was not present. Text branding is used until the original asset is provided; no replacement silhouette is fabricated. No LLM, OAuth, government portal, messaging, calendar or production integration is claimed.

See [walkthrough](docs/WALKTHROUGH.md), [security](docs/SECURITY.md), [limitations](docs/KNOWN_LIMITATIONS.md), and [status](docs/STATUS.md).
