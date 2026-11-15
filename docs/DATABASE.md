# Database

Initial migration: `apps/api/migrations/versions/1d907e8fbe2a_initial_schema.py`. From apps/api run `python -m alembic upgrade head`, then `python seed_demo.py` with DEMO_PASSWORD set. The migration is explicit, includes foreign keys, and has been applied/check-compared on a disposable SQLite database. PostgreSQL uses the same SQLAlchemy types but has not been executed here.

Tables: users, sessions, audit_events, records, documents, document_versions, citations, approvals, document_restrictions, preferences. UUID string primary keys; versions have content SHA256 and nanosecond creation ordering. Citations reference exact immutable versions and first-paragraph excerpts. Approval binds requester/reviewer to exact version. Department names are currently scope keys; normalized organizations/divisions/memberships remain future work.

Backup SQLite only while API stopped: copy the .db file to a protected backup. PostgreSQL: use pg_dump with managed credentials; encrypt backups, restrict access, test restoration in staging. Never commit database files. No production rollback should be attempted without backup and review. The initial down migration drops data and is intended for disposable development only.
