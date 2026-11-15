# Recovery gap audit

Audit baseline: feature branch fafcc92, preserving the uncommitted Next.js generated next-env.d.ts change. The recovery specification was read completely from the supplied local document. Remote fetch confirms main still has the initial README and feature branch matches local baseline. No history reset, new repository or merge.

## Visual source status

The reference and lotus paths in the specification are absent from the current checkout, origin feature tree, and searched local folders. User supplied download.png (copied to reference/agreed-profile-customize-ui.png), brahmagpt_lotus_white.svg, brahmagpt_lotus_white_transparent.png and image.png. All were visually inspected. Original assets are preserved under assets/. Exact new-UI comparison remains pending.

## Screen and workflow gaps

| Priority | Surface / workflow | Observed evidence | Required correction |
|---|---|---|---|
| P0 | Shell | apps/web/app/page.tsx holds every screen; sidebar starts with workspaces instead of New Chat/Search | AppShell, brand, accessible menus, correct hierarchy, routes |
| P0 | Brand | No assets/reference directories | Inspect and use actual supplied silhouette; no substitute |
| P0 | Responsive | style.css uses 76px sidebar and 10px labels | Drawer, readable touch targets, focus/escape handling |
| P0 | Top bar | Department is text; icons contain arbitrary glyphs | Membership selector, real search, notification inbox, ellipsis |
| P0 | My Profile | Identity paragraph only | Inner left navigation; banner/tabs; permitted edit/profile data |
| P0 | Setup & Access | Not implemented text | Normalized departments/divisions/memberships; requests; authorized decisions/expiry |
| P0 | Connected Apps | Not configured paragraph only | Provider catalogue, managed requests/activity, scoped connections and honest gates |
| P0 | AI & Models | Demo paragraph only | Actual provider availability, policy, persisted allowed defaults and tracked usage |
| P0 | Security | No session list or password change | Current-user sessions, revoke-other, password verification, security events |
| P0 | Notifications | No preferences/inbox | Persistent preferences, mandatory security, actual event-triggered inbox |
| P0 | Activity | Not implemented | Filtered own audit timeline; safe export; real counts |
| P0 | Preferences | Only theme is saved | Structured preferences, validation, refresh application; honest localization gates |
| P0 | Help | Links only | Search guides, persistent tickets and admin triage |
| P0 | Customize | Six labels share body state | Authorized catalogue, distinct queries, persisted favourites/order/hides/usage/requests |
| P1 | Chat | Request stored as generic record; no messages | Multi-turn conversation, explicit provider-unavailable response, history actions |
| P1 | Documents | Text entry/textarea, immutable versions and API citations exist | Real upload/extraction, editor controls, compare/lineage, contextual recommendations |
| P1 | Approval | Separate reviewer API exists; no timeline/notification or stale-version guard | Typed review UI; comments; immutable decisions; notifications; reapproval |
| P1 | Projects/Tasks | Generic record create/list | Collaboration, canonical assignments, dates, source links, meetings |
| P1 | Pension/Grievances | Same generic record form | Distinct case lifecycles, checklists, deficiencies/investigation/correspondence |
| P1 | Outreach | Not implemented | Consent/opt-out simulation, approvals, receipts; zero real sends |
| P1 | Admin | Audit API and same-department basic tool creation only | Access/tool/workflow/policy configuration and negative authorization tests |
| P1 | Infrastructure | Compose defined, no Docker executable found in PATH/standard locations | PostgreSQL migration verification, worker/storage integration; exact blockers |
| P0 | Verification | Seven baseline API tests; no browser suite/screenshots | Re-run baseline; add Playwright tests and screenshots; evaluate all 24 criteria |

## Execution sequence

0. Preserve baseline, inspect supplied imagery, establish tests/screenshots and acceptance records.
1. Stable routes/components and faithful global shell, chat/history/search, membership selector.
2. Nine Profile sections and six Customize tabs with relational persistence, permissions and browser coverage.
3. Source-document upload, editing, lineage, exact citations, recommendations, review/approval/export.
4. Distinct departmental workflows and outreach simulation.
5. Projects, canonical tasks, meetings and notifications.
6. Admin configuration, real/configuration-gated integrations, infrastructure and security.
7. Full 24-item evaluation, visual comparison, guides, verified commits/push/PR update.

Milestone 0/1 files: docs/RECOVERY_GAP_AUDIT.md, ACCEPTANCE_MATRIX.md, UX_SPEC.md; apps/web/components/{app-shell,sidebar,avatar-menu,top-bar,contextual-brahma}.tsx; app route files; lib/api.ts; apps/api/workspace.py; relational migration; backend tests; Playwright config/tests/screenshots. Existing document/auth code and tests remain available during refactoring.

Browser baseline found the Next.js development indicator intercepting avatar clicks. devIndicators is disabled to remove that obstruction.
