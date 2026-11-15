# Recovery feature matrix

Recovery baseline fafcc92 is preserved. This is not a completion declaration. See ACCEPTANCE_MATRIX.md for all 24 criteria.

| Area | State | Evidence / remaining work |
|---|---|---|
| Reference/lotus | INSPECTED + IN USE | Supplied files preserved; grayscale application uses exact SVG geometry |
| Shell | WORKING core | Correct hierarchy, avatar, membership selector, search/inbox, mobile drawer; browser tests. Domain routes still under recovery |
| Profile | WORKING core; advanced gaps | Nine real panels/gates, edit/avatar/private PDF, membership requests, security, activity, preferences, support. Quiet scheduling, delegation and translations absent |
| Customize | WORKING core | Server-filtered tabs; favourites/order/dismissals/usage/clear; real counts, requests and shortcuts; API/browser tests |
| Memberships | WORKING API | Request/decision/revoke/expiry and per-session scope isolation tested |
| Chat | REAL history; no live AI | Multi-turn messages and history actions; explicit provider-unavailable message |
| Original files | WORKING API + browser | PDF/DOCX/TXT validation, original bytes/hash and page/paragraph mapping. OCR/object storage absent |
| Drafting | DEMO | Explicit excerpts, immutable editable versions, retained evidence, separate recommendations/gaps; no legal verification |
| Citations/recommendations/diff | WORKING core | Exact original PDF/page/hash; source revocation, accepted suggestion revision and compare tested |
| Review | WORKING single-reviewer | Human return/resubmit/approve/reject, self/stale denial, immutable review events and notifications. Configurable multistep absent |
| Exports | REAL review copies | DOCX/PDF browser downloads; four file containers tested via API. Final issuance absent |
| Projects/tasks/cases | RECOVERY PENDING | Existing generic code preserved at /legacy; domain replacements not complete |
| Outreach | NOT IMPLEMENTED | No sends claimed |
| Admin | PARTIAL REAL | Access decisions, support triage, protected audit; configuration builder absent |
| External providers | NOT CONFIGURED | Requests persist; no OAuth/sync/send claimed |
| Infrastructure | PARTIAL / NOT RUN | SQLite migrations verified; Docker/PostgreSQL/Redis worker/object storage unverified |
| Browser | WORKING | Baseline and four recovery scenarios passed; screenshots saved |
| Production readiness | NOT READY | Remaining acceptance failures and security/classification review required |
