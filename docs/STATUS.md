# Recovery status - 2026-11-16

This is a verified recovery milestone, not completion of the master specification. All 24 acceptance criteria have an explicit evaluation in ACCEPTANCE_MATRIX.md.

| Area | Status | Evidence |
|---|---|---|
| Global shell/Profile/Customize | REAL core; advanced gaps | Supplied logo/reference inspected, routed panels, persistence/permissions and browser checks |
| Documents/source citations/review | REAL workflow with DEMO drafting | Original files/pages/paragraphs, keyword-selected excerpts, recommendations, immutable revisions/diff, separate review and review-copy exports |
| Projects/canonical tasks/cases | REAL illustrative core | Membership, collaboration, linked tasks/calendar, distinct pension/grievance transitions and negative permission tests |
| Outreach | DEMO SIMULATED | Consent/review/receipts/opt-out/feedback; zero real messages or calls |
| Admin/tool builder/agent task preview | REAL limited scope | Version-1 form configuration/activation, scoped entries; explicit typed preview/confirm/idempotency/audit |
| Hosted AI/OAuth/government/real communications | REQUIRES CREDENTIALS + IMPLEMENTATION | No external connection is claimed functional |
| PostgreSQL/Compose/Redis worker/object storage | NOT VERIFIED LOCALLY / INCOMPLETE | Docker absent from inspected locations. CI migration/browser jobs configured; actual remote result separate |
| Production readiness | NOT READY | Classification/security/retention/operations and remaining workflow criteria require completion and review |

## Completed local checks

- `python -m pytest -q`: 17 passed; one test-client deprecation warning.
- `python -m ruff check apps/api scripts`: passed.
- `npm run lint`: passed with no warnings after cleanup.
- `npm run typecheck`: passed.
- `npm run build`: passed (all current routes).
- E2E_PASSWORD set locally, `npm run test:e2e`: 8 passed; 32.9 seconds in the final recorded run.
- Disposable SQLite: `alembic upgrade head` and `alembic check`: passed, no new operations. Migration head 3bf7d91b7e1d.
- `npm audit`: zero findings after resolving the development lint glob dependency. No force/legacy peer resolution was used.
- `python scripts/check_secrets.py`: passed for private-key/GitHub-token/AWS-key patterns. This is a limited scan, not a full audit.
- Homepage and API health returned HTTP 200. Local URLs: http://localhost:3000 and http://127.0.0.1:8000/docs.

Screenshots: docs/screenshots contains login/home, all nine Profile panels, Customize Recommended/All Tools, mobile, Department Work, pension/grievance details, document evidence, project detail, tasks, approvals and admin. REFERENCE_COMPARISON.html shows the conceptual reference and actual captures together. Pixel-identical fidelity and automated screenshot-diff regression are not claimed.

Original data/history were preserved. The pre-recovery SQLite database has a local ignored backup. Original UI remains at /legacy for continuity. A pre-existing generated next-env.d.ts difference is deliberately left untouched.

See CONTINUATION.md for the exact next recovery instruction. GitHub delivery SHA/PR and remote CI results are verified separately in the handoff.

## Pension and outreach expansion

Both employee and social welfare scheme families now have a persisted pension register, scheme filters, 16 internal pension operation types and separate human review/return/completion. CSV/XLSX pension and outreach audience imports have persisted preview, validation, explicit confirmation, duplicate prevention, source identity and SHA-256 evidence. Connection requests are available but live website/API/database adapters remain not configured. Outreach now supports recorded feedback and escaped CSV simulation reports. Full usage and limits: PENSION_AND_LEGACY.md.

Latest pension expansion verification: 20 API tests and 10 browser tests passed; frontend typecheck, lint and production build passed; API Ruff and limited secret scan passed. Local SQLite upgraded through 6ac7d9e25f10 with no Alembic model differences. Live external connectors, scheme-specific entitlement calculations and production services remain incomplete.
