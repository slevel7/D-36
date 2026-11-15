# Pension and legacy system workflows

The local workspace supports both Government employee and Social welfare pension records. Scheme family and scheme name are persisted separately. These are internal case management workflows: scheme-specific eligibility rules, pension calculations, sanction powers, payment execution and statutory deadlines are not configured.

## Pension register and work

Open Department Work → Pension. Filter by scheme family, register a proposal, or import an existing system export. Open a case and select Pension register to record PPO/beneficiary reference, service dates, life certificate receipt/due dates, monthly reconciliation status and evidence notes.

Create a pension work item for service verification, family pension, revision, commutation, gratuity, arrears, life certificate, bank change, payment reconciliation, restoration, recovery, transfer, scheme eligibility, beneficiary verification, renewal or suspension/resumption. These operations record work and evidence; they do not calculate entitlements. Submit to a separate authorised reviewer, who can return or approve the item. Only the case owner or assigned officer can record completion after approval. Every transition is retained in case activity. Supporting documents remain in the case Files tab.

## Existing system imports

Open Pension → Import / Connect Existing System. Download the CSV template, export records from the authorised source, and use the template headings. Supported uploads: UTF-8 CSV or XLSX; maximum 2 MB, 500 data rows, 20 MB expanded workbook. Formula cells are rejected. Only the first worksheet is imported.

Pension headers: `external_id,pensioner_alias,case_type,retirement_date,summary,scheme,scheme_name`. Required: external_id, pensioner_alias, case_type, summary, scheme. Retirement dates use YYYY-MM-DD. Scheme is exactly Government employee or Social welfare. Case types: Retirement, Family, Revision, Clarification, New beneficiary, Renewal, Disability, Survivor. No source status or approval is trusted: imported cases start REGISTERED with evidence verification unchecked.

The preview persists the file SHA-256, source name, rows and validation results. No cases are created until confirmation. Any invalid row blocks confirmation. Duplicate source-name/external-ID combinations within the same department are skipped; existing records are never overwritten. Repeating confirmation returns the stored result. Preview/history are private to the importing officer and active department. Use a consistent source name across exports to retain duplicate detection. This is snapshot import, not automatic synchronisation or reconciliation of changed source records.

Connection requests accept a system name, site address, desired API/website export/database export method and business purpose. They persist as REQUESTED_NOT_CONNECTED. No supplied URL is fetched; no browser login, scraping, database connection, credential storage or API sync is implemented. An approved system-specific adapter, API contract and credentials are still needed for live integration. Do not enter secrets in connection requests.

## Outreach

Open Outreach Agent and create a draft campaign. Import audience CSV/XLSX with `alias,consent`; consent must explicitly be true or false. Preview and confirm before audience records are created. Duplicate aliases are skipped without overwriting consent or opt-out. Import is restricted to the draft campaign owner and blocked after submission. Imported audiences still require language review and separate campaign approval. Only consented contacts without opt-out are eligible for the simulation.

Record feedback beside a contact; opt-out cannot be silently reversed. Download outreach report exports campaign, contact alias, consent, opt-out, simulation receipt and feedback. Spreadsheet formula prefixes are escaped in CSV reports. Delivery remains SIMULATED: no calls, SMS, WhatsApp, email or external provider actions occur.

## Verification

API tests cover scheme/register persistence and invalid dates, officer and reviewer separation, return/resubmission/approval/completion, preview without writes, duplicate skip and repeat confirmation, cross-department denial, connection requests, Excel audience import, consent and formula rejection. Browser tests cover pension import/register persistence and operation creation, audience import, feedback and report download. See STATUS.md for latest run results.
