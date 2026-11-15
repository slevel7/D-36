# Administration guide

Seed admin@example.test has platform_admin role in a separate administration scope. GET /admin/audit is role protected and does not grant document-content access. A platform admin can create basic tools in its own department through /records/tools; the dynamic multi-department tool configuration console is not implemented. Provisioning demo users occurs only through the explicit local seed script. There is no production account provisioning, password recovery, role editor or membership approval interface yet.

Inspect audit via an authenticated admin session; do not expose audit to employees. Audit is append-only through API routes but has no database anti-tampering control. Do not enter real citizen information or production secrets. Missing connectors and unsupported workflows must stay disabled until implemented and tested.
