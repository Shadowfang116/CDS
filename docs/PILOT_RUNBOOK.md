# CDS Internal Pilot Runbook

## 1. Purpose Of The Pilot

This runbook is for a controlled internal pilot of **Covenant Diligence Systems (CDS)** inside the law firm before any bank-facing demonstration. The purpose is to prove that one reviewer and one approver can process a Pakistan property finance case from intake through Bank Pack export using the governed CDS workflow.

Pilot success means:

- a case can be created, processed, reviewed, approved or rejected, and exported end-to-end
- high-risk Exceptions and Conditions Precedent are surfaced clearly
- Evidence and Annexures remain traceable
- audit history is complete
- the workflow is usable in under 5 minutes after OCR and background processing complete

## 2. What Must Not Be Uploaded

Do not upload the following into the internal pilot:

- real bank customer files unless the repository is private and the deployment is explicitly approved for confidential material
- CNIC scans containing live customer data unless the matter is approved for confidential pilot use
- live account statements, loan sanction letters, or internal bank approvals
- unrelated litigation files
- malware samples, encrypted archives, or password-protected files
- any document that the operator cannot lawfully handle

Use synthetic, anonymized, or explicitly approved pilot materials wherever possible.

## 3. Required Synthetic Or Sample Files

Prepare a small pilot set before starting:

- one sale deed or registry deed sample
- one Fard or Jamabandi sample
- one society NOC or authority approval sample
- one legal opinion or undertaking draft input
- one mixed-quality scanned PDF to test OCR review

Safe repository locations:

- `docs/pilot_samples/`
- `docs/pilot_samples_real_example/`

Local-only confidential pilot materials, if approved, must stay outside Git or inside the ignored `docs/pilot_samples_real/` folder.

## 4. User Roles Used In Pilot

### Admin

- creates users and oversees configuration
- can open cases, upload documents, correct workflow issues, and manage pilot setup
- may force actions only where policy allows

### Reviewer

- performs document intake review
- reviews OCR text, dossier autofill, Exceptions, Conditions Precedent, Evidence, and Annexures
- resolves or recommends Waiver where justified

### Approver

- receives matters in `Ready for Approval`
- reviews dossier, Exceptions, Conditions Precedent, Evidence, and audit trail
- issues final Approve or Reject decision

### Viewer

- read-only access for supervised observation
- may inspect case history, documents, and outputs but not alter workflow state

## 5. End-To-End Pilot Workflow

1. Log in with the assigned pilot role.
2. Create a new case and assign the correct borrower, property context, and regime if known.
3. Upload the approved pilot document set.
4. Wait for OCR and background processing to complete.
5. Open document pages and review OCR output page by page.
6. Correct OCR text where the extracted text would affect legal review, Exceptions, Conditions Precedent, or dossier accuracy.
7. Run dossier autofill and inspect the extraction candidates.
8. Review dossier fields and confirm only defensible values with supporting page-level evidence.
9. Run the rules engine.
10. Review the resulting Exceptions list.
11. Review the resulting Conditions Precedent list.
12. Attach Evidence and Annexures to each material Exception or Condition Precedent.
13. Resolve or mark Waiver only where the record supports it.
14. Move the case to `Ready for Approval` when the reviewer believes the file is decision-ready.
15. Approver opens the case, reviews dossier, Exceptions, Conditions Precedent, Evidence, Annexures, and audit timeline.
16. Approver issues `Approved` or `Rejected`.
17. Generate the Bank Pack export.
18. Download the export and verify the output package.
19. Review the audit timeline to confirm that each critical step is recorded.

## 6. Evidence And Annexure Review

For each material Exception or Condition Precedent:

- verify that the cited document and page number are correct
- confirm the OCR text or manual correction matches the underlying document
- ensure Annexures are labeled consistently and can be defended in front of a bank reviewer
- avoid unsupported Waiver recommendations

Evidence should always answer one of these questions:

- what is missing?
- what is inconsistent?
- what cures the issue?
- what supports the approver decision?

## 7. Export Verification

After approval or rejection workflow is complete:

- generate the Bank Pack
- download the output
- verify that dossier values match the final reviewed record
- verify that Exceptions and Conditions Precedent appear with the expected wording
- verify that Evidence and Annexures are represented in a reviewer-usable manner
- verify that draft discrepancy, undertaking, or internal opinion skeleton outputs are generated where applicable

If export fails, do not continue the pilot without logging the failure and root cause.

## 8. Common Errors And What To Do

### OCR does not complete

- check `docker compose ps`
- inspect worker logs with `docker compose logs worker --tail=200`
- confirm Redis and OCR service are healthy

### OCR text is materially wrong

- open the document page
- correct OCR text where needed
- rerun downstream review of dossier/extractions that depend on that text

### Dossier autofill looks incorrect

- reject weak extraction candidates
- confirm only supported values
- require page-level evidence for critical fields

### Rules appear incomplete

- confirm the case reached a reviewable state
- verify required documents were uploaded and typed correctly
- rerun rules after dossier review if the factual record changed

### Bank Pack export fails

- inspect API logs with `docker compose logs api --tail=200`
- confirm object storage is healthy
- confirm required templates are present

### Approval should not proceed

- keep case in review or reject it
- do not use Waiver as a substitute for missing legal support

## 9. Pilot Scoring

The pilot should be scored on:

- end-to-end completion of the full workflow
- accuracy of OCR where it affects legal conclusions
- correctness of dossier fields
- quality and defensibility of Exceptions and Conditions Precedent
- ability to attach and review Evidence and Annexures
- audit completeness
- export success
- elapsed reviewer time after processing completes

Target operating benchmark:

- complete one pilot case in under 5 minutes after processing

## 10. Troubleshooting Commands

Useful operator commands:

```powershell
docker compose ps
docker compose logs api --tail=200
docker compose logs worker --tail=200
docker compose logs ocr_service --tail=200
docker compose exec -T api alembic current
Invoke-WebRequest http://localhost:8000/api/v1/health/deep -UseBasicParsing
```

## 11. Expected Output / Verification

The pilot run is acceptable when the following are true:

- reviewer can process at least one case end-to-end
- approver can issue a decision
- Bank Pack export downloads successfully
- audit timeline shows the full chain of actions

Suggested verification steps:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/health/deep -UseBasicParsing
docker compose exec -T api alembic current
docker compose logs api --tail=100
docker compose logs worker --tail=100
```

Expected outcome:

- health endpoint returns `200`
- migrations are at head
- no blocking export or OCR errors appear in recent logs
