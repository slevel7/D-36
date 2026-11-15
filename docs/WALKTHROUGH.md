# Demo walkthrough

1. Set a local DEMO_PASSWORD, seed, start API and web using README. Sign in as employee@example.test. Expected: DEMO Pension and five navigation entries. Persistent state: a revocable session and login audit.
2. Open Pension under Department Work. Create a fictional record with title/description. Persistent state: scoped record; this is basic CRUD, not pension processing.
3. Open Documents. Create two separate **immutable reference source** documents with clearly fictional text: `DEMO: Completeness review is required.` and `DEMO: Service records are missing.` No actual law is represented.
4. Select both references and choose Draft office note. Expected: editable DEMO excerpt compilation, two source buttons and immutable draft version/citation records.
5. Click each Source button. Evidence shows exact original version, paragraph one, excerpt and body. The marked passage is paragraph one; source pagination is not claimed.
6. Review suggestions and unknown fields in the draft. Export DOCX/PDF review copies with provenance appendix. Manual save creates a new version; its citations and approval do not carry forward. Regrounding revisions is not implemented.
7. Submit the original grounded version to reviewer@example.test. Approval row references that exact immutable version.
8. Sign out; sign in as reviewer@example.test with your local password. Open Documents then Approval queue using contextual footer. Return for changes or approve. A separate reviewer is enforced server-side. Each decision is audited.
9. Other@example.test cannot access the source, draft, citation or export. No cross-department switching is implemented.
10. My Tasks and Projects support basic records. Meetings, task delegation, favourite persistence, OAuth and profile editing remain absent; no success is shown for those operations.
