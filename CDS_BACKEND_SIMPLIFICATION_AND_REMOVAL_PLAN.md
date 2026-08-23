# CDS Backend Simplification and Removal Plan

**Status:** Proposed  
**Objective:** Reduce CDS to the smallest backend that can reliably perform the bank-ready Punjab mortgage diligence loop, without rewriting the working gold path.

---

# 1. Why this simplification is needed

CDS is trying to do one relatively short institutional workflow:

```text
upload
  ↓
classify
  ↓
extract facts
  ↓
compare
  ↓
findings
  ↓
additional evidence
  ↓
re-evaluate
  ↓
resolve / waive
  ↓
decide
  ↓
bank pack
```

RUN 2 and RUN 3 have already demonstrated that this loop can work.

The current backend feels heavier than the product because it grew through multiple development phases. Each phase added routes, services, models, helper layers, OCR paths, dashboards, controls, verifications, digests, and alternate workflows.

The goal of this plan is **not** to rewrite CDS.

The goal is:

> Keep the complexity that a bank actually needs, remove duplicated/unused machinery, and make the backend structure mirror the product that CDS actually sells.

The target mental model is:

```text
EVIDENCE
   ↓
FACTS
   ↓
FINDINGS
   ↓
DECISION
   ↓
PACK
```

with security, audit, tenant isolation, and maker/checker wrapped around it.

---

# 2. Product boundary

For the current MVP, CDS is:

- Punjab-first;
- mortgage against society plot or urban house/apartment;
- evidence-backed structured dossier;
- Exceptions;
- Conditions Precedent;
- discrepancy / undertaking / opinion drafts;
- PASS / CONDITIONAL PASS / FAIL decision;
- Bank Pack;
- maker/checker;
- organisation isolation;
- audit trail.

Anything that does not materially support that workflow is not part of the core product for this phase.

---

# 3. Simplification rule

Use a **strangler refactor**, not a rewrite.

For every existing backend capability, classify it as:

```text
CORE
Required for RUN 3 and the bank workflow.

ADAPTER
Temporary compatibility layer used by the old frontend/API.

FROZEN
Not required for the core workflow; no new development.

DEV-ONLY
Useful for testing/demo/development but not production product logic.

DELETE-CANDIDATE
Appears unused/duplicated/dead. Remove only after caller tracing + regression tests.
```

No code is deleted because it "looks old."

Deletion requires proof.

---

# 4. Non-negotiable complexity — KEEP

The following complexity is real and should remain.

## 4.1 Infrastructure

Keep:

```text
FastAPI
Postgres
MinIO
Redis
Celery
ocr_service
Docker Compose
```

Do not simplify CDS into synchronous OCR or local-disk-only processing.

The infrastructure split is appropriate for an on-prem bank deployment.

## 4.2 Security and governance

Keep:

- organisation / tenant isolation;
- RBAC;
- Admin / Reviewer / Approver / Viewer;
- maker/checker enforcement;
- signed downloads;
- audit trail;
- immutable/append-only audit semantics;
- retention hooks;
- TLS readiness;
- backup guidance.

## 4.3 Evidence model

Keep:

- original uploaded file;
- Document;
- DocumentPage;
- OCR text per page;
- OCR confidence / quality;
- exact document + page evidence;
- corrections without destroying the original text.

## 4.4 Proposed vs confirmed facts

Keep the distinction:

```text
OCR / extraction
      ↓
candidate
      ↓
review
      ↓
confirmed dossier
```

For now:

- `OCRExtractionCandidate` remains the proposed-fact store;
- `CaseDossierField` remains the confirmed-fact store.

Do **not** introduce a major database migration merely to rename them to `Fact`.

The simplification should first happen at the service/API level.

## 4.5 Findings

Keep:

- Exception as its own domain object;
- CP as its own domain object.

Do not merge them in the database.

Expose them together through a `FindingView` / workbench read model.

## 4.6 Approvals

Keep:

- case decision approval;
- waiver proposal and waiver approval;
- reviewer ≠ approver;
- server-side maker/checker enforcement;
- reason + evidence + audit.

## 4.7 Bank Pack

Keep:

- draft preview;
- versioned issued pack;
- PDF;
- DOCX outputs;
- annexure references;
- export/download controls.

---

# 5. Accidental complexity — simplify or remove

The current pain is primarily duplication and parallel paths.

The main targets are:

1. two OCR stacks;
2. overlapping extraction / dossier services;
3. duplicate waiver paths;
4. duplicate old/new frontend-facing APIs;
5. dashboard/analytics systems that are not required to complete a Matter;
6. phase-specific and legacy routes;
7. generic rulepack content outside property legal diligence;
8. multiple ways to trigger extraction/evaluation manually;
9. duplicate vocabulary and read models around Case/Matter.

---

# 6. Target backend architecture

The backend should eventually be explainable through seven product domains:

```text
backend/app/domain/
│
├── matters/
│   ├── lifecycle.py
│   └── service.py
│
├── evidence/
│   ├── ingest.py
│   ├── classify.py
│   └── service.py
│
├── facts/
│   ├── extract.py
│   ├── validate.py
│   ├── arbitrate.py
│   └── service.py
│
├── findings/
│   ├── evaluate.py
│   └── service.py
│
├── approvals/
│   └── service.py
│
├── decisions/
│   └── service.py
│
└── packs/
    └── service.py
```

This is the **target organisational model**, not a mandatory one-shot directory move.

Existing working services can remain where they are while being called through these facades.

Cross-cutting infrastructure remains separate:

```text
backend/app/infrastructure/
│
├── storage/
├── queue/
├── auth/
├── audit/
└── database/
```

Again, do not create a new framework merely to make folders look clean.

The important point is one responsibility per service.

---

# 7. One canonical Matter pipeline

There should be one obvious happy-path pipeline.

## 7.1 Document arrival

```text
UPLOAD DOCUMENT
      ↓
STORE ORIGINAL
      ↓
CREATE PAGES
      ↓
GET TEXT
      ↓
CLASSIFY
      ↓
EXTRACT CANDIDATE FACTS
      ↓
VALIDATE / ARBITRATE
      ↓
PERSIST CANDIDATES
      ↓
RE-EVALUATE AFFECTED RULES
      ↓
UPDATE MATTER STATE
```

Create or designate one orchestration entry point, conceptually:

```python
process_document(case_id, document_id)
```

This service should orchestrate existing components.

It should not contain the extraction logic itself.

## 7.2 Reviewer confirms a fact

```text
CONFIRM FACT
     ↓
write confirmed dossier field
     ↓
audit
     ↓
re-evaluate dependent rules
```

Conceptual entry point:

```python
confirm_fact(case_id, candidate_id, value, reviewer_id)
```

## 7.3 Additional evidence

The user should only need:

```text
UPLOAD ADDITIONAL EVIDENCE
```

Backend should automatically:

```text
store
→ OCR/text
→ classify
→ extract
→ evaluate affected rules
```

The frontend must not permanently orchestrate each internal subsystem.

## 7.4 Decision

```text
findings state
      ↓
decision calculation
      ↓
readiness calculation
      ↓
reviewer submits
      ↓
approver decides
```

## 7.5 Pack

```text
approved/final reviewed state
      ↓
snapshot
      ↓
generate pack
      ↓
store version
      ↓
signed download
```

---

# 8. One source of truth per concept

This is the most important simplification rule.

## OCR text

**Source of truth:**

```text
ocr_service → DocumentPage
```

No second production OCR implementation.

## Document type

**Source of truth:**

one canonical document classification field / vocabulary.

`predicted_doc_type` may remain as a model suggestion, but rules must consume the canonical reviewed/persisted type.

## Proposed fact

**Source of truth:**

`OCRExtractionCandidate`.

## Confirmed fact

**Source of truth:**

`CaseDossierField`.

## Rulepack

**Source of truth:**

one configured active rulepack path.

No worker/API disagreement about rulepack location.

## Exception status

**Source of truth:**

Exception service/model.

## CP status

**Source of truth:**

CP service/model.

## Waiver

**Source of truth:**

approval workflow.

Direct mutation/PATCH waiver becomes legacy and is removed after the new workbench no longer uses it.

## Decision

**Source of truth:**

one backend decision service.

Do not duplicate decision rules in React.

## Bank Pack

**Source of truth:**

one export/pack service and version history.

---

# 9. OCR simplification

## Current problem

There are two OCR stacks:

```text
ocr_service/
```

which is the production path, and:

```text
backend/app/services/ocr_*.py
```

which contains a much larger set of mostly unreachable code.

This creates permanent confusion:

- fixes may land in the wrong stack;
- tests may measure dead code;
- engineers cannot easily tell which OCR path matters;
- maintenance work doubles.

## Plan

Do **not** delete the dead stack immediately.

First:

1. build/finish the OCR measurement baseline;
2. trace imports/callers;
3. verify production requests use `ocr_service`;
4. run RUN 3 and OCR regression tests;
5. mark dead OCR modules deprecated;
6. remove imports/references;
7. delete dead modules in a dedicated PR.

## Final state

```text
PDF / image
    ↓
ocr_service
    ↓
DocumentPage.ocr_text
```

Backend application services consume page text.

They do not contain a second OCR engine.

## Delete gate

Do not remove `backend/app/services/ocr_*.py` until all are true:

```text
[ ] no production import
[ ] no worker import
[ ] no API route import
[ ] no active test depends on it
[ ] OCR baseline exists
[ ] RUN 3 passes
[ ] docker compose smoke test passes
```

---

# 10. Dossier / extraction simplification

`dossier_autofill.py` has accumulated too many responsibilities.

The target should be:

```text
dossier_autofill.py
=
orchestrator / compatibility facade
```

not:

```text
OCR collector
+ extractor
+ classifier
+ HF client
+ party role system
+ quality gate
+ validator
+ arbitrator
+ persistence layer
+ dossier writer
```

Gradually split responsibilities into existing/new focused services:

```text
facts/read_pages.py
facts/extract.py
facts/validate.py
facts/arbitrate.py
facts/persist.py
```

Do this incrementally.

At each extraction:

```text
current code
      ↓
small service extracted
      ↓
old public function delegates to new service
      ↓
tests pass
      ↓
RUN 3 passes
```

Do not change semantics while reorganising code.

---

# 11. Do not add a new Fact database table yet

A canonical `Fact` concept is useful, but adding another table now could increase complexity.

Use a domain-level view first.

Conceptually:

```python
FactCandidate(
    key,
    value,
    normalized_value,
    source_document_id,
    page,
    confidence,
    review_status,
)
```

Map this onto the existing `OCRExtractionCandidate`.

Conceptually:

```python
ConfirmedFact(
    key,
    value,
    evidence,
    confirmed_by,
    confirmed_at,
)
```

Map this onto the existing `CaseDossierField`.

Rules should eventually consume these stable domain objects/read models rather than knowing storage details.

If this design proves clean, database consolidation can be considered later.

Not in the first simplification pass.

---

# 12. Rulepack simplification

The default MVP rulepack should only contain rules relevant to the CDS product scope.

The active Punjab mortgage pack should focus on:

```text
identity / authority required for mortgage
property identity
title / ownership chain
area / property mismatch
current revenue evidence
society / authority approvals
development dues
prior encumbrance / charge
tax / municipal evidence
mortgage/security perfection
required documents
material timeline gaps
```

Rules such as:

```text
salary slip
passport photograph
generic income verification
generic utility bill
co-applicant KYC
```

are credit-underwriting rules, not automatically part of property legal diligence.

Do not delete their history immediately.

Move them out of the active MVP rulepack into:

```text
docs/rulepacks/archive/
```

or a clearly non-active future/credit-underwriting pack.

The active pack must be obvious.

Suggested:

```text
docs/rulepacks/
├── punjab_mortgage_v1.yaml          # ACTIVE
└── archive/
    └── generic_mvp_legacy.yaml
```

`RULEPACK_PATH` points only to the active pack.

Keep applicability controls.

Do not hard-code RUN 3 values.

---

# 13. API simplification

The current backend exposes many route modules because the product grew in phases.

The target public product API should be understandable as:

```text
MATTERS
EVIDENCE
FACTS
FINDINGS
APPROVALS
PACKS
GOVERNANCE
```

Target conceptual API:

```text
POST /matters
GET  /matters/{id}

POST /matters/{id}/evidence
GET  /matters/{id}/evidence

GET  /matters/{id}/facts
POST /matters/{id}/facts/{candidate_id}/confirm

GET  /matters/{id}/findings
POST /matters/{id}/findings/{id}/resolve
POST /matters/{id}/findings/{id}/request-waiver

GET  /matters/{id}/decision
POST /matters/{id}/submit

GET  /matters/{id}/approvals
POST /approvals/{id}/decide

GET  /matters/{id}/pack
POST /matters/{id}/pack/preview
POST /matters/{id}/pack/issue
```

This does **not** mean rewrite all routes now.

First add a clean façade/read model for the new Workbench.

Old routes remain compatibility adapters until the old frontend stops calling them.

Then delete routes one family at a time.

---

# 14. Add one Workbench read model

The new Matter Workbench should not need 10–20 unrelated API calls merely to understand the Matter.

Create a backend read model such as:

```text
GET /matters/{id}/workbench
```

or keep the existing route namespace initially:

```text
GET /cases/{id}/workbench
```

Response should contain only the state needed to render the workbench shell:

```json
{
  "matter": {},
  "lifecycle_status": "Review",
  "decision": "FAIL",
  "readiness": {},
  "next_action": {},
  "documents": [],
  "dossier_progress": {},
  "findings": [],
  "pending_approvals": []
}
```

Do not include full OCR text for every page.

Page/document evidence remains lazy-loaded.

This simplifies the frontend/backend contract without changing storage.

---

# 15. Approval simplification

There must be one waiver workflow.

Target:

```text
Reviewer
  ↓
request exception_waive approval
  ↓
Approver
  ↓
approve/reject
  ↓
Exception becomes Waived if approved
```

The old direct:

```text
PATCH exception → waived
```

must become:

```text
LEGACY / DEPRECATED
```

Once the new Workbench no longer calls it:

1. search for all callers;
2. update tests;
3. reject new frontend usage;
4. remove the route/service path.

Maker/checker remains server-enforced.

---

# 16. Dashboard / analytics simplification

The bank diligence loop does not require the large dashboard subsystem.

Classify the following as **FROZEN** unless proven necessary for the Workbench:

```text
dashboard analytics
dashboard saved views
digests
case insights
activity analytics
portfolio charts
```

Do not add features to them.

After Inbox/Workbench is live:

1. trace frontend callers;
2. move management-only analytics behind Governance/Reports if needed;
3. remove unused route modules;
4. remove unused services/tests/components.

The default home becomes Inbox, not dashboard analytics.

---

# 17. Controls / playbooks / verifications simplification

Do not delete these merely because RUN 3 did not need every one.

First determine whether each concept is:

```text
a real bank control
or
an implementation-era abstraction
```

## Keep if it provides unique mandatory functionality

Examples:

- actual external registry verification;
- evidence completion requirement;
- mandatory security perfection check.

## Merge if it duplicates Findings or Evidence completeness

Examples:

- a "case control" whose only job is to say a document is missing;
- a checklist duplicating rule-engine missing-evidence output;
- a verification record duplicating a confirmed evidence/fact state.

Target principle:

```text
Missing evidence → Finding / completeness state

Confirmed source fact → Dossier / Fact

External verification → Verification only if a real external check occurred
```

Do not keep a separate subsystem merely because a table exists.

---

# 18. Email / webhooks / integrations

For the MVP core:

```text
email
webhooks
digests
external integrations
```

are not required to complete RUN 3.

Classify them as:

```text
FROZEN / ENTERPRISE-LATER
```

Do not develop them during core simplification.

Do not delete a production integration if it is already actively used.

If no production caller exists:

- keep behind Governance if inexpensive;
- otherwise archive/remove after caller tracing.

---

# 19. Development/demo code

Classify development-only functionality explicitly.

Examples may include:

```text
demo seeding
pilot scripts
synthetic corpus tools
cohort PDF generation
debug endpoints
temporary phase utilities
```

These should live under:

```text
scripts/
tests/
devtools/
```

where possible.

They should not look like production domain services.

Do not delete test utilities needed for RUN 3 regression.

---

# 20. Phase-specific files

Files/routes with names such as:

```text
*_phase10.py
*.bak
legacy_*
old_*
```

are immediate audit candidates.

For each:

1. search imports;
2. search route registration;
3. search frontend calls;
4. search tests;
5. classify;
6. remove only when zero live callers exist.

A `.bak` file should not remain in the application package.

Version control already stores history.

---

# 21. Simplification workstreams

## WS-S0 — Freeze and baseline

**Goal:** prevent complexity growth before cleanup.

Actions:

- no new backend product features;
- no Surya/Paddle work;
- no new generic rule systems;
- no analytics expansion;
- no new workflow framework;
- record current RUN 3 result;
- run full backend tests;
- record Docker Compose health;
- record active route list;
- record active worker tasks.

Create:

```text
AI_context/backend_simplification/
├── 01_inventory.md
├── 02_dependency_map.md
├── 03_delete_candidates.md
├── 04_worklog.md
└── 05_decisions.md
```

Do not delete code in WS-S0.

---

## WS-S1 — Inventory every backend subsystem

**Goal:** know what is actually alive.

For every:

```text
backend/app/api/routes/*.py
backend/app/services/*.py
backend/app/services/**/*.py
ocr_service/**
worker task
```

record:

```text
file
purpose
production caller
frontend caller
worker caller
tests
RUN 3 dependency
classification
```

Classification:

```text
CORE
ADAPTER
FROZEN
DEV-ONLY
DELETE-CANDIDATE
UNKNOWN
```

No `UNKNOWN` item can be deleted.

---

## WS-S2 — Define the core service façade

**Goal:** make the existing backend look simple before deleting internals.

Introduce/standardise these application-level operations:

```text
create_matter
add_evidence
process_document
confirm_fact
evaluate_matter
resolve_finding
request_waiver
submit_matter
decide_approval
preview_pack
issue_pack
```

These should call existing working logic.

Do not rewrite implementations yet.

The Workbench should use this façade.

---

## WS-S3 — One production OCR path

**Goal:** remove ambiguity around OCR.

Actions:

- verify all production OCR uses `ocr_service`;
- finish measurement baseline required by Q4;
- mark backend OCR stack deprecated;
- remove active imports;
- delete unreachable OCR modules in a dedicated change;
- keep only shared OCR data contracts if actually needed.

Verification:

```text
RUN 3 passes
OCR tests pass
worker uses ocr_service
no backend ocr_* production callers
```

---

## WS-S4 — Simplify extraction / dossier orchestration

**Goal:** shrink `dossier_autofill.py` responsibility without changing behaviour.

Extract one responsibility at a time:

```text
page reading
fact extraction
validation
candidate arbitration
candidate persistence
```

Keep `autofill_dossier()` as a compatibility façade during migration.

Each extraction requires:

```text
existing tests pass
new focused tests pass
RUN 3 passes
```

Do not change database schema.

---

## WS-S5 — Simplify rulepacks

**Goal:** one obvious active Punjab mortgage rulepack.

Actions:

- identify rules needed for MVP property legal diligence;
- preserve gold generic rule logic;
- move generic KYC/credit-underwriting rules out of active pack;
- keep rule applicability;
- rename active pack clearly;
- update `RULEPACK_PATH`;
- add rulepack load test;
- RUN 3 must remain unchanged.

Do not delete historical rule definitions until archived.

---

## WS-S6 — Unify Findings + waiver application layer

**Goal:** one service contract over Exceptions/CPs while preserving their distinct models.

Create:

```text
FindingView
```

with:

```text
type
id
rule_id
severity
status
description
evidence_refs
cp_text
hard_stop
waivable
waiver_state
```

Remove direct frontend dependency on separate internal data shapes where practical.

Then:

- migrate waiver to approval-only;
- deprecate direct PATCH waive;
- remove it after zero callers.

---

## WS-S7 — Simplify API routes

**Goal:** reduce route surface after Workbench migration.

First introduce clean Workbench/product routes or façade endpoints.

Then retire, in batches:

```text
unused dashboard routes
saved-view routes
legacy phase routes
duplicate document routes
duplicate evaluation routes
legacy direct-waiver routes
unused insight/digest routes
```

Each removal batch needs:

```text
caller search
frontend build
backend tests
RUN 3
```

Do not remove Admin/Governance endpoints still needed for RBAC/audit/security.

---

## WS-S8 — Remove obsolete secondary product systems

**Goal:** remove or quarantine systems not required for the product.

Candidates may include:

```text
digests
unused case insights
unused dashboard analytics
unused playbook abstractions
duplicate controls
duplicate evidence checklists
unused webhook/email systems
old demo services
```

Decision per subsystem:

```text
KEEP
MOVE TO GOVERNANCE
ARCHIVE
DELETE
```

No deletion without dependency proof.

---

## WS-S9 — Remove old frontend compatibility backend

After the new:

```text
Inbox
Matter Workbench
Approver
Pack
```

has replaced the old UI:

- find endpoints used only by old `case-workspace`;
- remove old frontend route consumers;
- remove backend adapters no longer called;
- remove old case-detail aggregation code;
- keep redirects where needed.

This is the final strangler cutover.

---

# 22. Deletion order

Do not begin with the largest file.

Delete in lowest-risk order.

Recommended:

```text
1. .bak / clearly accidental files
2. unreachable phase-specific helpers
3. unused dev/demo production services
4. unused dashboard/analytics routes
5. legacy direct waiver path
6. duplicate route families
7. dead backend OCR stack
8. obsolete compatibility orchestration
```

The OCR stack is large but should be deleted later because its blast radius is larger and Q4 explicitly requires measurement first.

---

# 23. Removal checklist for every file/subsystem

Before deletion:

```text
[ ] grep/search imports
[ ] search FastAPI router registration
[ ] search Celery task imports
[ ] search frontend API calls
[ ] search scripts
[ ] search tests
[ ] search Docker/Compose references
[ ] search environment variables
[ ] run targeted tests
[ ] run full backend tests
[ ] run frontend build if API-facing
[ ] run RUN 3
[ ] document decision
```

If any live caller remains, do not delete.

---

# 24. Commands for the audit

Run from:

```powershell
cd C:\Users\fahad\Desktop\bank-diligence-platform\bank-diligence-platform
```

Create the simplification branch **after the current Workbench work is safely committed**:

```powershell
git status
git add .
git commit -m "feat: complete gold-backed matter workbench"
git checkout -b refactor/cds-backend-core
```

Create context folder:

```powershell
New-Item -ItemType Directory -Force AI_context\backend_simplification
New-Item -ItemType File -Force AI_context\backend_simplification\01_inventory.md
New-Item -ItemType File -Force AI_context\backend_simplification\02_dependency_map.md
New-Item -ItemType File -Force AI_context\backend_simplification\03_delete_candidates.md
New-Item -ItemType File -Force AI_context\backend_simplification\04_worklog.md
New-Item -ItemType File -Force AI_context\backend_simplification\05_decisions.md
```

Useful inventory commands:

```powershell
Get-ChildItem backend\app\api\routes -File | Sort-Object Name | Select-Object Name,Length

Get-ChildItem backend\app\services -File | Sort-Object Name | Select-Object Name,Length

Get-ChildItem backend\app\services -Recurse -File |
    Sort-Object FullName |
    Select-Object FullName,Length

Get-ChildItem ocr_service -Recurse -File |
    Sort-Object FullName |
    Select-Object FullName,Length
```

Find references before deleting a candidate:

```powershell
git grep -n "documents_phase10"
git grep -n "waiveException"
git grep -n "dashboard_views"
git grep -n "case_insights"
git grep -n "digest"
git grep -n "ocr_"
```

Do not interpret grep output mechanically.

Inspect whether each reference is production, test-only, or dead.

---

# 25. Test gate

Every simplification PR must pass:

```powershell
Push-Location backend

python -m pytest tests -q

Pop-Location
```

Frontend-facing changes:

```powershell
Push-Location frontend

npm run lint
npm run build

Pop-Location
```

Docker:

```powershell
docker compose up -d --build api worker ocr_service
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 worker
docker compose logs --tail=100 ocr_service
```

Gold regression:

```powershell
powershell -File scripts\dev\run_cds_gold_001_e2e.ps1
```

Do not reuse RUN 1 as product validation.

RUN 3 semantics are the regression lock.

---

# 26. Target end-state API/product contract

The frontend should eventually only need to think in:

```text
Matter
Evidence
Facts
Findings
Decision
Approval
Pack
```

It should not need to know:

```text
which OCR stack ran
which candidate gate ran
which rule evaluation endpoint to manually trigger
which dashboard subsystem owns a count
which phase-specific document route exists
which internal model stores a field
```

The backend owns orchestration.

The Workbench consumes a stable product contract.

---

# 27. Target end-state code characteristics

The simplification is successful when:

```text
✓ one production OCR path exists

✓ one canonical document type vocabulary exists

✓ one candidate path exists

✓ one confirmed-fact path exists

✓ one rulepack is active for Punjab mortgage

✓ one waiver path exists

✓ one decision service exists

✓ one pack issuance path exists

✓ one Workbench read model exists

✓ Exception and CP remain legally distinct

✓ old dashboard systems are not required to complete a Matter

✓ no phase-specific route is needed for the core flow

✓ no frontend action manually orchestrates the internal pipeline

✓ every remaining service has one explainable responsibility
```

---

# 28. What must NOT happen during simplification

Do not:

```text
❌ rewrite FastAPI from scratch
❌ replace Postgres
❌ replace MinIO
❌ remove Celery/Redis
❌ merge Exception + CP DB models
❌ remove audit
❌ weaken tenant isolation
❌ remove maker/checker
❌ auto-confirm OCR candidates
❌ introduce a new workflow engine
❌ add event sourcing
❌ add Kafka
❌ add microservices because the code feels large
❌ create a new Fact table before the service model proves itself
❌ delete the dead OCR stack before Q4's measurement gate
❌ modify RUN 3 semantics to make refactoring easier
```

The objective is fewer concepts, not newer technology.

---

# 29. Recommended active/frozen/removal categories

Initial classification to verify during WS-S1:

## CORE — keep and invest

```text
auth / RBAC / org scoping
matters/cases lifecycle
documents + pages
MinIO
ocr_service
canonical document classification
candidate extraction
candidate validation
candidate arbitration
confirmed dossier
rule engine
active Punjab mortgage rulepack
Exceptions
CPs
approvals
waivers through approvals
audit
bank pack / exports
signed downloads
Celery worker
```

## FROZEN — no new development

```text
dashboard analytics
saved dashboard views
digests
case insights
generic management reporting
webhook expansion
email automation
playbook expansion
generic evaluation UI concepts
```

Keep temporarily if callers exist.

## REVIEW / MERGE

```text
case controls
evidence checklist
verifications
dossier vs dossier-field service layers
duplicate document routes
duplicate evaluation triggers
old Case workspace backend aggregations
```

These may contain useful behavior, but must not remain separate concepts if they duplicate Evidence / Facts / Findings.

## DELETE-CANDIDATE

Verify before deleting:

```text
*.bak files
unreachable backend OCR stack
unused phase-specific route modules
dead demo production services
legacy direct PATCH waiver
unused dashboard endpoints after Inbox migration
unused digest/insight services
old compatibility adapters after Workbench cutover
```

---

# 30. Milestones

## Milestone A — No new accidental complexity

Backend feature freeze is active.

RUN 3 still passes.

Inventory complete.

## Milestone B — Simple façade

Workbench uses a small Matter/Evidence/Facts/Findings/Approval/Pack contract.

Old internals still work underneath.

## Milestone C — One OCR stack

Only `ocr_service` performs production OCR.

Dead backend OCR code removed.

## Milestone D — Small extraction core

`dossier_autofill.py` is a compatibility/orchestration function, not the place where every extraction concern lives.

## Milestone E — One active mortgage rulepack

Generic unrelated KYC/credit rules are outside the active legal-property pack.

## Milestone F — One approval/waiver path

No direct waiver mutation path remains.

## Milestone G — Legacy product systems removed

Inbox + Workbench no longer depend on Dashboard/Insights/Digests/phase routes.

## Milestone H — Core backend can be explained in 30 seconds

The explanation should be:

> A Matter receives Evidence. The worker turns Evidence into proposed Facts. Reviewers confirm important Facts. Rules compare the Facts and create Exceptions and CPs. New Evidence re-runs affected rules. Once Findings are resolved or waived, the Reviewer submits the Matter, an independent Approver decides it, and CDS freezes and issues the Bank Pack. Everything is organisation-scoped and audited.

If that explanation matches the code architecture, simplification is complete.

---

# 31. Definition of Done

Backend simplification is complete when all of the following are true:

```text
[ ] RUN 3 passes unchanged

[ ] full backend tests pass

[ ] frontend Workbench passes its tests/build

[ ] one production OCR stack

[ ] one active Punjab mortgage rulepack

[ ] one canonical classification path

[ ] candidate arbitration preserved

[ ] proposed != confirmed remains enforced

[ ] one waiver workflow through approvals

[ ] maker/checker server-side

[ ] one decision source of truth

[ ] one Bank Pack issuance path

[ ] no dead phase-specific production routes

[ ] no `.bak` application files

[ ] no unused dashboard/digest/insight subsystem is loaded in core flow

[ ] frontend does not manually coordinate OCR → extract → evaluate as separate product modules

[ ] core route/service inventory is documented

[ ] every deleted file has a recorded dependency check

[ ] audit and tenant isolation remain intact
```

---

# 32. Final principle

Do not measure success by how many files are deleted.

Measure success by whether the backend now mirrors the product:

```text
EVIDENCE
   ↓
FACTS
   ↓
FINDINGS
   ↓
DECISION
   ↓
PACK
```

The correct backend is not the smallest possible codebase.

It is the smallest codebase that still preserves:

```text
evidence traceability
human confirmation
bank rules
maker/checker
auditability
tenant isolation
versioned institutional output
```

Everything else must justify its existence.
