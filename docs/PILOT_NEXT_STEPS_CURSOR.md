# CDS Pilot Next Steps — Cursor / Manual Workflow

This file is the practical next-step guide for working locally in Cursor on Windows after the production-ready repo push.

## Where we are

The repo has been cleaned and pushed to GitHub.

Confirmed release state:

```text
Repository: Shadowfang116/CDS
Remote: https://github.com/Shadowfang116/CDS.git
Release branch: codex/release/bootstrap-stable
Latest release commit: db0ec50 Prepare CDS repo for production-ready pilot release
```

The repo now contains the production-style foundation:

- Next.js frontend
- FastAPI backend
- Postgres
- Redis
- MinIO
- Celery worker/beat
- OCR service
- HF extractor
- Docker Compose
- Production Docker Compose
- Caddy reverse proxy
- `.env.example` files
- deployment docs
- backup script
- RBAC/auth/audit/rules/export architecture

The next step is not to add random features. The next step is to turn the cleaned repo into a controlled internal pilot that can process 10 synthetic/sample Punjab property finance cases end-to-end.

## Most important next action

Merge or expose the clean release branch.

Right now, the clean production-ready work is on:

```text
codex/release/bootstrap-stable
```

But GitHub default branch may still be:

```text
master
```

You should open a PR:

```text
codex/release/bootstrap-stable -> master
```

Then merge it after reviewing the diff.

This matters because anyone opening GitHub normally may see the default branch, not the clean release branch.

## Local verification commands

Open PowerShell in repo root:

```powershell
cd C:\Users\fahad\Desktop\bank-diligence-platform\bank-diligence-platform
```

Check branch:

```powershell
git branch --show-current
```

Expected:

```text
codex/release/bootstrap-stable
```

Check latest commit:

```powershell
git log --oneline -3
```

Expected top commit should show something like:

```text
db0ec50 Prepare CDS repo for production-ready pilot release
```

Check working tree:

```powershell
git status --short
```

Expected: clean output.

## Pilot objective

The internal pilot must prove this workflow:

```text
Create case
Upload title/property documents
Run OCR
Review OCR pages
Autofill dossier
Run rules
Review Exceptions
Review Conditions Precedent
Attach Evidence/Annexures
Move to Ready for Approval
Approve/Reject
Export Bank Pack
Download and review DOCX/PDF output
```

Target result:

```text
Complete bank pack in under 5 minutes after processing.
```

Quality target:

```text
For 10 synthetic/sample cases, flag at least 80% of high-risk gold-standard items.
False positives should be tracked and explainable.
```

## What you should create next

Create these docs if they do not already exist:

```text
docs/PILOT_RUNBOOK.md
docs/PILOT_EVALUATION_TEMPLATE.md
docs/SECURITY_HARDENING_BACKLOG.md
```

A Codex-ready execution plan has also been added in:

```text
docs/PILOT_NEXT_STEPS_CODEX.md
```

Use that file as the agent prompt/brief.

## Cursor workflow

### Step 1 — Pull the latest release branch

```powershell
git fetch origin
```

```powershell
git checkout codex/release/bootstrap-stable
```

```powershell
git pull origin codex/release/bootstrap-stable
```

### Step 2 — Create a pilot branch

```powershell
git checkout -b codex/pilot/runbook-and-cleanup
```

### Step 3 — Ask Cursor to read the repo context

Use this Cursor prompt:

```text
You are working in the CDS / Covenant Diligence Systems repo.

Read these files first:
- README.md
- docs/PILOT_NEXT_STEPS_CODEX.md
- docker-compose.yml
- docker-compose.prod.yml
- backend/app/api/router.py
- backend/app/services/rule_engine.py
- backend/rules/diligence_rules.yaml
- frontend/lib/api.ts

Do not edit anything yet.

After reading, summarize:
1. Current product architecture
2. Current pilot readiness
3. Files that should be added next
4. Any risky gaps before internal pilot
```

### Step 4 — Ask Cursor to create the pilot docs

Use this prompt:

```text
Create the following files based on docs/PILOT_NEXT_STEPS_CODEX.md:

1. docs/PILOT_RUNBOOK.md
2. docs/PILOT_EVALUATION_TEMPLATE.md
3. docs/SECURITY_HARDENING_BACKLOG.md

Use practical bank/legal language. Keep the workflow low-tech-user friendly.
Do not add real client data, CNICs, bank documents, property documents, or generated files.
Do not modify source code unless necessary.
```

### Step 5 — Run local checks

Backend:

```powershell
cd backend
```

```powershell
python -m compileall app
```

```powershell
python -m pytest
```

```powershell
cd ..
```

Frontend:

```powershell
cd frontend
```

```powershell
npm run lint
```

```powershell
npm run build
```

```powershell
cd ..
```

Compose:

```powershell
docker compose config
```

```powershell
docker compose -f docker-compose.prod.yml config
```

### Step 6 — Stage safe files only

```powershell
git status --short
```

Stage docs only:

```powershell
git add docs/PILOT_RUNBOOK.md docs/PILOT_EVALUATION_TEMPLATE.md docs/SECURITY_HARDENING_BACKLOG.md docs/PILOT_NEXT_STEPS_CURSOR.md docs/PILOT_NEXT_STEPS_CODEX.md
```

Check staged files:

```powershell
git diff --cached --name-only
```

Do not stage:

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
node_modules/
.next/
.venv/
```

### Step 7 — Commit

```powershell
git commit -m "Add CDS pilot planning docs"
```

### Step 8 — Push

```powershell
git push -u origin codex/pilot/runbook-and-cleanup
```

## After the planning docs are merged

Move into pilot testing.

Create 10 synthetic case packs:

```text
Case 01 — Clean registry house
Case 02 — Missing e-stamp evidence
Case 03 — Society plot missing mortgage permission
Case 04 — CNIC mismatch
Case 05 — Registry reference mismatch
Case 06 — Litigation keyword risk
Case 07 — Revenue record missing
Case 08 — Constructed house missing completion/map evidence
Case 09 — Possession evidence gap
Case 10 — Mixed Urdu/English low-quality scan
```

For each case, record:

```text
Expected flags
Actual flags
Missed flags
False positives
OCR quality
Dossier accuracy
Export success
Time to bank pack
```

## What not to do yet

Do not start selling to banks yet.

Do not upload real client documents to a public repo.

Do not add more features before proving the full case flow.

Do not overclaim timeline/title-chain intelligence until the timeline evaluator performs real date-chain analysis.

Do not treat Docker Compose passing as the same thing as a successful legal workflow pilot.

## The real next milestone

The next milestone is:

```text
One synthetic Punjab property finance case processed end-to-end, with a downloadable bank pack, reviewed by a real lawyer.
```

After that:

```text
10 synthetic cases measured against gold-standard expected exceptions.
```

Only after that should you start preparing a bank demo deck or sales outreach.

## Expected output / verification

After completing this workflow, run:

```powershell
git status --short
```

Expected:

```text
clean working tree
```

Run:

```powershell
git log --oneline -5
```

Expected latest commit:

```text
Add CDS pilot planning docs
```

Run:

```powershell
git branch --show-current
```

Expected:

```text
codex/pilot/runbook-and-cleanup
```
