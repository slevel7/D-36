# Reproducible recovery walkthrough

Use fictional fixtures in apps/web/e2e/fixtures, your local seed password, and separate employee/reviewer browser sessions. The local demo can enter as employee automatically; use /login for a reviewer/admin. No external service is needed or claimed.

| Step | Visible action and expected result | Persistent state |
|---|---|---|
| 1 | Start API/web; open home. Five exact workspaces, supplied lotus, approved department selector and avatar-only profile menu appear. | Session, login/demo-entry audit; existing records preserved |
| 2 | Open My Profile, Edit Profile, change a demo contact/display field, save and reload. | Profile/preference row and audit event |
| 3 | Request another department/division with reason/duration. Admin opens /admin, reviews and confirms. Switch only after approval. | AccessRequest decision, Membership, Notification and per-session scope; existing source ACL remains enforced |
| 4 | Open Pension, New Proposal; use a fictional alias and summary. The case has a DEMO internal reference. | Typed case, sample checklist and first event |
| 5 | Advance Collecting/Verification. Record a deficiency, resolve it and complete the sample checklist. | Checklist/deficiency rows, case status/events |
| 6 | Upload the sample PDF and DOCX in Documents or the case Files tab. | Immutable original bytes/hash, source Document/Version and page/paragraph passages; optional case link |
| 7 | Choose Draft with sources, select both files and enter an office-note brief about missing supporting records. | DEMO excerpt draft version, exact citations, recommendations and generation audit |
| 8 | Click Source chips. The viewer shows original version/hash and actual PDF page or DOCX paragraph; a text passage is marked. | Read is permission-checked; original file unchanged |
| 9 | Accept/dismiss recommendations; edit only supported facts/suggestions and save twice. Compare versions. | New immutable versions; exact retained evidence; suggestion status; no inherited approval |
| 10 | Submit for Review and confirm the designated separate reviewer. | Approval request bound to exact version; reviewer notification and audit |
| 11 | Reviewer opens /approvals, inspects submitted-version link and returns with comment. Employee revises/resubmits; reviewer approves the latest version. | Immutable review events, decision/status, notifications; self/stale approvals blocked |
| 12 | Export DOCX/PDF; optionally evidence review XLSX/PPTX. | Real generated review copies with source metadata; export audit. No official final issuance |
| 13 | Add a follow-up from the case, or type a task into contextual Brahma, Preview task, inspect and Confirm. | Canonical Task with source link; typed proposal/confirmation and idempotent action audit |
| 14 | Create a project, invite an authorised colleague, assign a task, attach a source, post discussion and schedule an internal meeting. | Project membership/tasks/file links/posts/meeting and notifications; no external URL |
| 15 | Favourite an available tool, reorder, launch it, refresh and inspect Recently Used. | Favourite order, permission-filtered usage; optional recents can be cleared without removing audit |
| 16 | Profile Connected Apps shows Not configured. Request a provider for a stated reason. | Internal request only; no OAuth connection, sync or external data transfer |
| 17 | Register a fictional grievance; assign/investigate, save a proposed response, submit review, return/revise, resolve as separate reviewer and close. | Distinct grievance state/events, draft correspondence and notifications |
| 18 | Create a simulated campaign with consented aliases; record language review, submit, approve separately, confirm simulation and record opt-out. | Campaign review/activity, SIMULATED receipts and opt-out; real sends remain zero |
| 19 | Admin creates fields/states for a departmental form, saves draft and explicitly activates. Authorised staff launch and save an entry. | Configuration version/activation, scoped ToolDefinition, entry/state and audit |

Browser automation covers the main Profile/Customize, document review, project, pension verification, grievance investigation, simulation and tool-builder paths. Not every step above has complete browser coverage; exact API/browser gaps remain in ACCEPTANCE_MATRIX.md. Richer case reports, reminder workers, hosted AI/OAuth, production policies, full approval chains and final issuance remain unfinished.
