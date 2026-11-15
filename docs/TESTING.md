# Testing

At repository root: `python -m pytest -q`; `python -m ruff check apps/api`. From apps/web: `npm.cmd run typecheck`, `npm.cmd run build`. From apps/api against a fresh disposable database: `python -m alembic upgrade head`, `python -m alembic check`.

Six pytest scenarios cover password salt/verification; authentication/CSRF/revocation/admin denial; grounded compilation/two evidence sources/reviewer return/resubmit/approve/export/cross-department refusal/original immutability/changed-revision review rejection; preferences/search/source-access revocation including draft/citation/export/approval refusal. Each test resets an isolated in-memory SQLite schema.

Browser tool was attempted but returned No browser is available. No UI screenshots, Playwright E2E, accessibility audit or visual regression has been performed. PostgreSQL/Docker and external integration tests have not run. Passing a TypeScript build is not evidence of every module working. FastAPI TestClient emits a deprecation warning about httpx; tests still pass with pinned dependencies.

Live smoke: DEMO_PASSWORD set locally, `python scripts/smoke_test.py` passed through Next.js /api proxy; homepage HTTP 200. `python scripts/check_secrets.py` is a lightweight pattern scan, not a full secret audit.

Login regression: five failed attempts return HTTP 429 with Retry-After; a deterministic clock test verifies countdown/expiry and successful login afterward without deleting audit events. Email trims surrounding whitespace and ignores case; password contents remain exact. Login disables repeated submissions and offers a visibility toggle.
