# Architecture

Next.js App Router renders a monochrome client workspace. Same-origin `/api/*` rewrites to loopback FastAPI, avoiding cross-origin cookie requirements. SQLAlchemy persists users, sessions, audit events, department records, documents, immutable versions, citations and approval requests. SQLite supports credential-free development; PostgreSQL uses psycopg through DATABASE_URL. Redis/MinIO are infrastructure configuration only.

Sessions store only SHA256 digests of random bearer tokens. CSRF tokens are bound to sessions. Source retrieval is scoped by department before drafting and again on citation opening and export. Deterministic drafting quotes source paragraph one and marks unknown fields. It is not an LLM provider.

Master-spec entities, granular policies, memberships, jobs and external adapters remain to be implemented; see feature matrix.

## Recovery modules

Next.js now has explicit routes and shared AppShell/session/UI components. Typed client contracts live in apps/web/lib/api.ts. Profile/Customize, document workspace, project/task/case/outreach and configured-tool screens are separate components. Existing UI is retained at /legacy. FastAPI core routes are preserved; workspace.py/workspace_models.py add profile/membership/catalogue/chat; files.py adds originals/passages/recommendations/review history; work.py adds collaboration/canonical tasks/distinct cases/simulation; configured_tools.py adds scoped form configurations/entries and transactional typed task previews. Routers register after the existing core models to preserve the current import and migration contracts.

Relational migrations extend the original schema through 3bf7d91b7e1d. Original file blobs are currently database-backed; Redis workers and object-storage integration remain to be implemented. No live LLM or external provider transfer occurs. The optional local automatic session is disabled by default and requires explicit development flags, loopback access and a custom header.
