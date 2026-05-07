# CDS Pilot Next Steps — Codex Execution Plan

This file is the execution brief for Codex after the production-ready bootstrap release.

## Current confirmed repo state

- Repository: `Shadowfang116/CDS`
- Release branch: `codex/release/bootstrap-stable`
- Latest release commit: `db0ec50 Prepare CDS repo for production-ready pilot release`
- Product name: Covenant Diligence Systems / CDS
- MVP focus: Punjab-first property finance diligence
- Pilot target: father’s law firm first, then bank-facing demonstrations

## Strategic context

CDS is no longer just an OCR/document tool. It is intended to be a bank-ready, on-prem deployable platform that converts Pakistan property deal documents into:

1. Structured dossier
2. Exceptions list
3. Conditions Precedent list
4. Draft discrepancy letter / undertaking / internal legal opinion skeleton
5. Bank pack export in DOCX/PDF form
6. Audit trail and role-controlled review workflow

The repo now has a credible production-style pilot base, but the next step is not to randomly add features. The next step is to make the platform usable for a controlled internal pilot and prove one end-to-end case flow.

## Immediate objective

Prepare the repo for a clean internal pilot run at the law firm.

The pilot success definition is:

> A reviewer can create a case, upload documents, run OCR, review extracted text, autofill dossier fields, run rules, review Exceptions/CPs, attach evidence, approve/reject, and export a bank pack in under 5 minutes after processing.

## Create a new branch

Create a new working branch from the latest release branch:

```bash
git checkout codex/release/bootstrap-stable
git pull origin codex/release/bootstrap-stable
git checkout -b codex/pilot/runbook-and-cleanup
```

## Task 1 — Add pilot runbook

Create:

```text
docs/PILOT_RUNBOOK.md
```

The runbook must be written for a low-tech law firm user and a technical operator.

Include these sections:

1. Purpose of the pilot
2. What not to upload
3. Required synthetic/sample files
4. User roles used in pilot
5. End-to-end workflow
6. Evidence and annexure review
7. Export verification
8. Common errors and what to do
9. Pilot scoring
10. Expected output / verification

The workflow must cover:

```text
login
create case
upload documents
wait for OCR
review document pages
correct OCR text if needed
autofill dossier
review dossier fields
run rules
review Exceptions
review Conditions Precedent
attach evidence
resolve/waive where appropriate
move case to Ready for Approval
approve/reject
export bank pack
download export
verify audit timeline
```

Use bank language throughout:

- Exceptions
- Conditions Precedent
- Waiver
- Evidence
- Annexures
- Approver
- Bank Pack

Do not use casual product language.

## Task 2 — Add pilot evaluation template

Create:

```text
docs/PILOT_EVALUATION_TEMPLATE.md
```

This should be a markdown table for 10 sample cases.

Columns:

```text
Case No.
Property Type
Regime
Document Set
Expected High-Risk Flags
Actual High-Risk Flags
Missed Flags
False Positives
OCR Confidence
Dossier Accuracy
Bank Pack Exported? 
Processing Time
Reviewer Notes
Approver Notes
```

Also add a scoring section:

```text
High-risk recall target: >= 80%
False positives: tracked and explainable
Bank pack export: must succeed for every pilot case
Processing time: target under 5 minutes after processing
```

## Task 3 — Add security hardening backlog

Create:

```text
docs/SECURITY_HARDENING_BACKLOG.md
```

Include the following items with priority and acceptance criteria:

1. Make GitHub repo private before real documents or bank-specific materials are added
2. Add database-level audit log immutability
3. Add MinIO object storage backup automation
4. Add restore drill documentation
5. Add route-level RBAC and tenant-scope audit
6. Add object-key org isolation test
7. Add secret scanning with gitleaks or equivalent
8. Add production TLS/cert renewal verification
9. Add admin user bootstrap command/runbook
10. Add retention policy enforcement test

## Task 4 — Clean remaining product naming

Search for old public-facing names:

```text
Bank Diligence Platform
bankdiligence
Case Diligence Suite
```

Replace public-facing strings with:

```text
Covenant Diligence Systems
CDS
```

Do not break package names, import paths, database names, or historical migration names unless safe.

If an old string remains intentionally, list it in the final report.

## Task 5 — Check default branch problem

The release branch is clean, but GitHub default branch is still `master`.

Add a note to the final report recommending one of:

```text
Open PR: codex/release/bootstrap-stable -> master
```

or

```text
Change GitHub default branch to codex/release/bootstrap-stable
```

Recommended: open PR and merge into `master`.

## Task 6 — Verify no confidential files are committed

Before staging, confirm these are not tracked:

```text
.env
.env.production
docs/pilot_samples_real/
tmp/
uploads/
exports/
ocr_output/
*.pdf
*.docx
*.xlsx
*.csv
```

Only generic templates may be tracked.

Use:

```bash
git status --short
git ls-files | grep -E "(\.env$|pilot_samples_real|uploads|ocr_output|exports|tmp/|\.pdf$|\.docx$|\.xlsx$|\.csv$)" || true
```

Review every match manually.

## Task 7 — Run verification checks

Backend:

```bash
cd backend
python -m compileall app
python -m pytest
cd ..
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
cd ..
```

Compose:

```bash
docker compose config
docker compose -f docker-compose.prod.yml config
```

If a check fails, do not hide it. Fix the smallest issue or report the exact blocker.

## Task 8 — Commit and push

Stage only safe files:

```bash
git add docs/PILOT_RUNBOOK.md docs/PILOT_EVALUATION_TEMPLATE.md docs/SECURITY_HARDENING_BACKLOG.md
```

If product naming cleanup changed files, stage those too after review.

Commit:

```bash
git commit -m "Add CDS pilot runbook and hardening backlog"
```

Push:

```bash
git push -u origin codex/pilot/runbook-and-cleanup
```

## Final report format

Return:

1. Branch and commit
2. Files created/updated
3. Product naming cleanup summary
4. Confidential file audit result
5. Checks run and results
6. Remaining blockers
7. Expected output / verification

## Expected output / verification

After completion, these commands should work:

```bash
git status --short
git log --oneline -3
git branch --show-current
```

Expected:

```text
git status --short returns clean
latest commit is Add CDS pilot runbook and hardening backlog
current branch is codex/pilot/runbook-and-cleanup
```
