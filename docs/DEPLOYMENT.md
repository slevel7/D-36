# Deployment and operations

Development only. See README for Windows/Linux setup. No hosted deployment was created. Run Docker Desktop manually before `docker compose up -d`; if docker is not on PATH install official Docker Desktop and enable WSL2. Set local service secrets in .env. Export DATABASE_URL into the API process; compose .env is not automatically imported by Python. Verify database connectivity by `python -m alembic current` from apps/api. Use a fresh disposable DB for the first migration; existing seed-created SQLite databases can be recreated only when their data is disposable, or stamped after careful schema comparison.

Ports: 3000 web, 8000 API, 5432 PostgreSQL, 6379 Redis, 9000/9001 MinIO. If occupied, stop your own process or choose new ports and update API_URL. Missing Redis currently does not affect implemented API routes because jobs are not integrated.

Before any staging/production deployment: independent security review; granular ACL and classification; proper account lifecycle/MFA/reset; secret management; TLS and COOKIE_SECURE=true; restricted database/service network; tested PostgreSQL migrations/backup/restore; retention policy; incident response; monitored worker reliability and real tenant authorizations. Do not use local demo users in production. Compose is local infrastructure, not a production orchestration plan. Free-tier resources may sleep, lose ephemeral files, or lack pgvector/worker support.

Git delivery uses existing origin slevel7/D-36 only. Feature branch is feat/brahmagpt-full-platform. Never force-push or rewrite main. Push with `git push -u origin feat/brahmagpt-full-platform`, then create a draft PR into main describing current limitations. No auto-merge.
