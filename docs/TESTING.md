# Testing

At repository root: `python -m pytest -q`; `python -m ruff check apps/api`. From apps/web: `npm.cmd run typecheck`, `npm.cmd run build`. From apps/api against a fresh disposable database: `python -m alembic upgrade head`, `python -m alembic check`.

Seven pytest scenarios cover password salt/verification; authentication/CSRF/revocation/admin denial; grounded compilation/two evidence sources/reviewer return/resubmit/approve/export/cross-department refusal/original immutability/changed-revision review rejection; preferences/search/source-access revocation including draft/citation/export/approval refusal. Each test resets an isolated in-memory SQLite schema.

Browser tool was attempted but returned No browser is available. No UI screenshots, Playwright E2E, accessibility audit or visual regression has been performed. PostgreSQL/Docker and external integration tests have not run. Passing a TypeScript build is not evidence of every module working. FastAPI TestClient emits a deprecation warning about httpx; tests still pass with pinned dependencies.

Live smoke: DEMO_PASSWORD set locally, `python scripts/smoke_test.py` passed through Next.js /api proxy; homepage HTTP 200. `python scripts/check_secrets.py` is a lightweight pattern scan, not a full secret audit.

Login regression: five failed attempts return HTTP 429 with Retry-After; a deterministic clock test verifies countdown/expiry and successful login afterward without deleting audit events. Email trims surrounding whitespace and ignores case; password contents remain exact. Login disables repeated submissions and offers a visibility toggle.

Local demo-entry regression verifies default-disabled, development-only, loopback-only, custom-header checks; employee-only identity; admin denial; preserved CSRF enforcement; logout revocation; and disabled production/secure-cookie modes.

## Recovery verification supersedes the earlier foundation counts

17 API scenarios pass; 8 browser scenarios pass. From apps/web run npm run lint, npm run typecheck, npm run build and (with local E2E_PASSWORD set) npm run test:e2e. First install the matching browser with npx playwright install chromium. The preserved baseline.capture.ts records the old UI and is excluded from normal .spec.ts runs. Current suites: recovery.spec.ts, documents.spec.ts, work.spec.ts and preview.spec.ts. Browser tests create fictional data in the development database, so use an isolated copy if preserving a clean demo dataset matters. CI uses a fresh database. Automated pixel-diff goldens, PostgreSQL local runtime and complete 24-item acceptance remain unfinished.

Latest pension expansion verification: 20 API tests and 10 browser tests passed; frontend typecheck, lint and production build passed; API Ruff and limited secret scan passed. Local SQLite upgraded through 6ac7d9e25f10 with no Alembic model differences. Live external connectors, scheme-specific entitlement calculations and production services remain incomplete.
