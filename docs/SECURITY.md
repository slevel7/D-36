# Security and permissions

This is a development foundation requiring independent security review before real data or deployment. Keep the public repository synthetic. Use a private deployment for departmental records after approval.

Implemented: scrypt with random per-password salt; random server sessions hashed at rest, eight-hour expiry, httpOnly strict-samesite cookies, CSRF validation on authenticated writes, database login failure throttling, current-session revocation, department filters including citations and exports, exact-role admin guard, append-only application audit writes. Platform admins cannot read other departments automatically.

Limitations: one department per user; no document ACL/classification, division policy, MFA, reset mechanism, distributed abuse prevention, database-level audit immutability, retention/legal hold, secret vault, antivirus, HTTP security headers or production TLS configuration. Login throttling keys hash email but require stronger privacy controls in production. COOKIE_SECURE must be true behind HTTPS. Source text is untrusted content quoted by a deterministic compiler, never executed as instructions. All exports are explicitly review copies. Draft edits create new versions without copied citations/approval. They cannot be submitted until a future regrounding workflow is implemented; generate a new grounded draft for now.

Do not enter real citizen data. Do not expose the development servers on public interfaces. Recover demo access through local reseeding after deleting only your local disposable database; there is no production reset flow.

Optional local preview: DEMO_AUTO_LOGIN=true together with APP_ENV=development enables a loopback-only /auth/demo endpoint requiring a custom request header. It creates only the fixed seeded DEMO employee session; admin selection is impossible. It remains disabled by default, with secure-cookie production configuration, and outside development. Existing CSRF/department/resource permissions still apply. Do not use with real data or expose this mode through an external reverse proxy.
