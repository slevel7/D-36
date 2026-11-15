# Architecture

Next.js App Router renders a monochrome client workspace. Same-origin `/api/*` rewrites to loopback FastAPI, avoiding cross-origin cookie requirements. SQLAlchemy persists users, sessions, audit events, department records, documents, immutable versions, citations and approval requests. SQLite supports credential-free development; PostgreSQL uses psycopg through DATABASE_URL. Redis/MinIO are infrastructure configuration only.

Sessions store only SHA256 digests of random bearer tokens. CSRF tokens are bound to sessions. Source retrieval is scoped by department before drafting and again on citation opening and export. Deterministic drafting quotes source paragraph one and marks unknown fields. It is not an LLM provider.

Master-spec entities, granular policies, memberships, jobs and external adapters remain to be implemented; see feature matrix.
