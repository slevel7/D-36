# Administrator guide

Only an authorised platform administrator can enter /admin or its protected APIs. The demo admin is scoped to DEMO Administration and has no automatic access to other departments' document contents.

The access review queue shows the requested department/division/role/duration and reason. A human must confirm approval/rejection with a comment. Self-review is blocked. Approved memberships appear in the requester's selector; expiry/revocation is rechecked server-side. Roles apply in the approved department and do not overwrite the user's permanent identity role.

Support tickets can be moved to In Progress/Resolved with a response; the requester sees the persisted response and notification. No automatic diagnostic upload or email is claimed.

The departmental tool builder creates bounded typed fields, allowed roles and a simple state sequence. Saving produces an immutable version-1 DRAFT configuration; explicit activation with a review comment makes it available. The tool remains filtered by department and role at discovery, launch and entry APIs. Staff cannot bypass required fields or skip configured states. New configuration versions/edit history, complex approval chains and policy binding remain incomplete.

Audit API access is protected; application routes append events instead of editing history. This is not database-level tamper resistance. Full organization/user provisioning, official employment editing, classification/ACL policy management, approved document templates, retention, provider credentials/budgets and feature-flag administration are not yet complete. Do not provision real departmental data or secrets through this demonstration build.

Use WINDOWS_SETUP.md, STATUS.md, ACCEPTANCE_MATRIX.md and KNOWN_LIMITATIONS.md for exact setup, verification and outstanding work. No production or official-government deployment is claimed.
