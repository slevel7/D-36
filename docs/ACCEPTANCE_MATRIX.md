# Acceptance matrix

Status values: PASS only with recorded evidence; PARTIAL, FAIL, BLOCKED and NOT EVALUATED are not completion. Baseline is fafcc92. All 24 criteria remain part of the recovery acceptance contract.

| # | Requirement | Implementation/test evidence path | Result | Screenshot |
|---|---|---|---|---|
| 1 | Shell/logo/navigation | Visual and browser assertions | PARTIAL; shell browser checks pass; remaining domain routes under recovery | Not captured |
| 2 | Reference fidelity/desktop/mobile | Screenshots + mobile drawer test | PARTIAL; reference/screenshots inspected; responsive differences documented | Not captured |
| 3 | Multi-turn chat/history | API + conversation browser test | PARTIAL; private multi-turn history; no hosted AI | Not captured |
| 4 | Nine Profile sections | Profile API and browser scenarios | PARTIAL; nine real panels/gates; quiet scheduling/delegation/translations incomplete | Not captured |
| 5 | Access request/admin decision/scope | Membership API + browser + IDOR | API PASS; browser admin approval pending | Not captured |
| 6 | Six Customize tabs/persistence | Catalogue API + browser reload | CORE PASS; persistence browser and ordering/usage API tests | Not captured |
| 7 | Project collaboration flow | Project browser workflow | FAIL baseline | Not captured |
| 8 | Pension lifecycle | Pension browser workflow | FAIL baseline; generic records | Not captured |
| 9 | Grievance lifecycle | Grievance browser workflow | FAIL baseline; generic records | Not captured |
| 10 | Outreach simulation/consent | Simulation API + browser + no-send assertion | FAIL baseline | Not captured |
| 11 | Admin configurable tool/permissions | Tool builder browser + negative API | FAIL baseline | Not captured |
| 12 | PDF/DOCX upload/extraction/reject invalid | Upload API + fixture files | FAIL baseline | Not captured |
| 13 | Grounded drafting/recommendations/gaps | Existing API tests + full browser | DEMO core PASS; editable excerpts, recommendations/gaps and browser review flow | Not captured |
| 14 | Exact citation viewer/revocation | Existing citation API tests + browser positioning | Core PASS; original PDF page/mark and revoked-source API checks | Not captured |
| 15 | Version compare/originals/four exports | Diff API + format validation + browser | Review-copy scope PASS; diff/original bytes/four formats tested; final issuance absent | Not captured |
| 16 | Human review/return/reapproval/audit/notification | Existing reviewer API tests + workflow browser | Single-reviewer scope PASS; notifications and stale denial tested | Not captured |
| 17 | Contextual action preview/confirm/log | Agent proposal API + browser | FAIL baseline | Not captured |
| 18 | Unified tasks/filters/comments/calendar | Task API + browser | FAIL baseline; basic records | Not captured |
| 19 | Authorized global search/IDOR | Search + source permission negative tests | PARTIAL; scoped content/chat search added; broad indexing incomplete | Not captured |
| 20 | Unconfigured provider honesty | Provider catalogue + browser states | Provider gates PASS; real requests and not-configured catalogue | Not captured |
| 21 | Restart persistence | Persistent SQLite/Postgres restart + browser | NOT EVALUATED | Not captured |
| 22 | Admin/sensitive/file authorization | Negative API suite | PARTIAL baseline; existing admin/source checks | Not captured |
| 23 | Compose/Postgres/CI/checks | Migration + Compose + test/build/E2E commands | BLOCKED Docker; browser baseline pending | Not captured |
| 24 | Remote branch/PR/SHA/secret checks | git verification + scanner | BASELINE remote fafcc92; PR #1 exists | Not captured |

## Latest evidence

API: 12 passed; Ruff, TypeScript and production build passed. Playwright: recovery.spec.ts 3 passed; documents.spec.ts 1 passed; baseline capture previously 1 passed. See UX_SPEC.md for actual screenshot paths. Remaining criteria retain FAIL/PARTIAL/BLOCKED; no complete-product claim.
