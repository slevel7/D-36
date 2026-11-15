# Recovery feature matrix

Recovery baseline fafcc92 is preserved. This is not a completion declaration. See ACCEPTANCE_MATRIX.md for all 24 criteria.

| Area | State | Evidence / remaining work |
|---|---|---|
| Reference/lotus | INSPECTED + IN USE | Supplied files preserved; grayscale application uses exact SVG geometry |
| Shell | WORKING core | Correct hierarchy, avatar, membership selector, search/inbox, mobile drawer; browser tests. Domain routes still under recovery |
| Profile | WORKING core; advanced gaps | Nine real panels/gates, edit/avatar/private PDF, membership requests, security, activity, preferences, support. Quiet scheduling, delegation and translations absent |
| Customize | WORKING core | Server-filtered tabs; favourites/order/dismissals/usage/clear; real counts, requests and shortcuts; API/browser tests |
| Memberships | WORKING API | Request/decision/revoke/expiry and per-session scope isolation tested |
| Chat | REAL history; no live AI | Multi-turn messages/history actions; broader browser history coverage pending; explicit provider-unavailable message |
| Original files | WORKING API + browser | PDF/DOCX/TXT validation, original bytes/hash and page/paragraph mapping. OCR/object storage absent |
| Drafting | DEMO | Explicit excerpts, immutable editable versions, retained evidence, separate recommendations/gaps; no legal verification |
| Citations/recommendations/diff | WORKING core | Exact original PDF/page/hash; source revocation, accepted suggestion revision and compare tested |
| Review | WORKING single-reviewer | Human return/resubmit/approve/reject, self/stale denial, immutable review events and notifications. Configurable multistep absent |
| Exports | REAL review copies | DOCX/PDF browser downloads; four file containers tested via API. Final issuance absent |
| Projects/tasks/cases | REAL core, advanced gaps | Distinct relational project collaboration, canonical linked tasks/calendar and illustrative case transitions; API/browser tested. Advanced reports/configuration/reminder worker incomplete |
| Outreach | DEMO SIMULATED | Consent, separate review, persistent delivery receipts, opt-outs/feedback; API/browser tested. Zero real sends |
| Admin | PARTIAL REAL | Access/support review, protected audit and version-1 departmental form builder with explicit activation, role/department-filtered execution |
| External providers | NOT CONFIGURED | Requests persist; no OAuth/sync/send claimed |
| Infrastructure | PARTIAL / NOT RUN | SQLite migrations verified; Docker/PostgreSQL/Redis worker/object storage unverified |
| Browser | WORKING local | 8 current scenarios passed, including preview capture; screenshots saved. Automated pixel-diff goldens absent |
| Production readiness | NOT READY | Remaining acceptance failures and security/classification review required |

Latest API suite: 17 passed. Frontend lint, typecheck and production build passed. Dependency audit reports zero findings after a patched minimatch override. Full acceptance remains PARTIAL/BLOCKED as recorded in ACCEPTANCE_MATRIX.md.
