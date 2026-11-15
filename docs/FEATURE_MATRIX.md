# Feature matrix

| Capability | State | Evidence / remaining work |
|---|---|---|
| FastAPI + SQLAlchemy | WORKING locally | SQLite test database; PostgreSQL config unverified |
| Login, salted scrypt, revocable httpOnly cookie, CSRF | WORKING locally | pytest authentication scenario |
| Department scoping, admin denial | WORKING limited | Cross-department document/citation/export tests; source revocation tested; full ACL/classification absent |
| Next.js monochrome workspace | BUILD VERIFIED | Typecheck + production build passed; browser unavailable |
| Projects, Tasks, Pension, Grievances | BASIC RECORDS ONLY | Persistent create/list; full lifecycle, assignments, comments, reminders not done |
| Immutable source text, draft versions | WORKING locally | Originals cannot be edited; revised drafts require regrounding |
| Grounded AI drafting | DEMO | Explicit excerpt compilation from two distinct sources; no LLM/legal verification |
| Citations | WORKING API | Exact source version/hash/paragraph and excerpt; browser click-through not yet tested |
| Approvals | WORKING limited | Separate designated reviewer; approve/return/reject; no configurable multistep workflows |
| DOCX/PDF export | WORKING API | Review copies only, evidence appendix, ZIP/PDF signatures tested |
| Upload/OCR/preview, PPTX/XLSX | NOT DONE | Text entry only; no file upload endpoint |
| Profile | PARTIAL | Identity display, current-session logout, backend-persisted theme preferences; nine complete sections not done |
| Customize | PARTIAL | Discovery navigation only; no persistent favourites or recents |
| Chat and contextual Brahma | DEMO/PARTIAL | Requests stored; no autonomous or provider AI response |
| Admin | PARTIAL | Protected audit API and tool creation; no full management console |
| Access requests / memberships | NOT DONE | One department per user in current schema |
| Outreach | NOT DONE | No simulated or real sends |
| Notifications / worker | NOT DONE | No fake counters or deliveries |
| External connectors / embeddings | REQUIRES CREDENTIALS + IMPLEMENTATION | No connector is functional |
| Docker PostgreSQL/Redis/MinIO | CONFIGURED, NOT RUN | Docker unavailable on host |
| Alembic initial schema | WORKING SQLite | upgrade head + check passed; PostgreSQL not run |
| Browser E2E, visual regression | NOT RUN | No browser available |
| Lotus | MISSING ASSET | Supplied original unavailable in inspected paths |

A working API slice does not imply completion of the master specification. The repository is an incremental foundation.
