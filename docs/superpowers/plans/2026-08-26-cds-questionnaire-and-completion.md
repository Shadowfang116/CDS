# CDS Questionnaire and Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the questionnaire-driven CDS workflow from matter intake through evidence review, waiver/approval, and a production-ready private deployment.

**Architecture:** Extend the existing Next.js dashboard, FastAPI case/workbench APIs, PostgreSQL models, and Docker Compose deployment in place. The questionnaire becomes structured matter-intake data that drives existing borrower/transaction applicability and required-evidence logic; it does not replace the rule engine or create a second case workflow. OCR and legal findings remain provisional until a human reviewer confirms them, and the existing maker-checker approval boundary remains intact.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL JSONB, Celery, MinIO, Docker Compose, Caddy, PowerShell, pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-cds-local-ui-and-deployment-design.md`

## Global Constraints

- Preserve CDS terminology: Inbox, Matter, File, Evidence, Work, Exceptions, Conditions Precedent, approvals, audit, and Bank Pack.
- Keep OCR and extraction provisional until a human confirms them; never silently convert uncertain extraction into verified legal fact.
- Missing information must mark the matter incomplete and identify the missing evidence.
- Risk must use a readable severity label and explanation, not color alone.
- Keep Exceptions separate from Conditions Precedent.
- Preserve tenant scoping, role checks, audit logging, and maker-checker separation.
- Keep the desktop-first scope; do not introduce a mobile redesign in this work.
- Do not claim OCR accuracy until representative samples and ground truth exist in `datasets/urdu_ocr/samples/` and the measured result is recorded in `AI_context/04_worklog.md`.
- Update `AI_context/` in the same session as every OCR, extraction, evaluator, or gold-run change.
- Do not deploy publicly until a target private Linux host, domain, TLS plan, production secrets, backup location, and rollback owner are supplied.
- Preserve existing unrelated worktree changes.

---

## Current Baseline and Files

The current repository already contains most workflow primitives but not the complete questionnaire flow:

- New matter creation currently accepts only `title` in `backend/app/schemas/case.py` and `frontend/app/(dashboard)/dashboard/cases/page.tsx`.
- Borrower and transaction context is inferred/persisted by `backend/app/services/dossier_autofill.py`; the rule engine consumes it in `backend/app/services/rule_engine.py`.
- The dashboard queue is `frontend/components/inbox/inbox-view.tsx`; the main workbench is `frontend/components/workbench/matter-workbench.tsx` with `file-pane.tsx`, `evidence-pane.tsx`, `evidence-viewer.tsx`, `findings-list.tsx`, `work-pane.tsx`, and `decision-strip.tsx`.
- The legacy case surface is `frontend/components/cases/case-workspace.tsx`, with supporting `DocumentsPanel.tsx`, `ExceptionsPanel.tsx`, and `AuditPanel.tsx`.
- Email/password login exists in `backend/app/api/routes/auth.py` and `frontend/app/login/page.tsx`; no company SSO/OIDC flow is present.
- Approval and waiver services already exist in `backend/app/services/approvals.py` and `backend/app/api/routes/approvals.py`; the UI surface is `frontend/app/approvals/page.tsx`.
- Production deployment is already scaffolded by `docker-compose.prod.yml`, `Caddyfile`, `.env.production.example`, `docs/ops/DEPLOYMENT_PROD.md`, `docs/ops/ENVIRONMENT_MATRIX.md`, and `scripts/ops/preflight_prod.ps1`.
- AI_context reports that RUN 2 demonstrated document classification, five meaningful findings, additional-evidence resolution, and automatic re-evaluation, but still lacks reliable Sale Deed area extraction, explicit Fard issue-date extraction, and the historical-tax/waiver gold path.

## Definition of Done

The plan is complete only when all of the following are demonstrated on a clean local run and recorded:

1. A reviewer can create a matter by answering the intake questionnaire, save/resume it, and see the answers reflected in the Matter header and required-evidence view.
2. Uploading the RUN 3 corpus produces the intended area mismatch, stale-Fard, and historical-tax findings without false generic borrower findings.
3. Additional evidence resolves the intended findings; historical tax remains open until a reviewer proposes and a separate checker approves a waiver.
4. The final decision and Bank Pack contain the same findings, evidence references, resolutions, and waiver decision.
5. Admin/Reviewer/Viewer access remains enforced; the existing Approver checker boundary remains enforced for waiver and final decision actions.
6. Email login works, and company SSO works through a configured OIDC provider with tenant/role mapping and audit events.
7. The production preflight, backup, restore, health, TLS, and rollback procedures are executable on the selected private Linux host.

---

### Task 1: Freeze the current baseline and convert the questionnaire into an acceptance matrix

**Files:**
- Read: `AI_context/README.md`
- Read: `AI_context/02_findings.md`
- Read: `AI_context/03_plan.md`
- Read: `AI_context/05_decisions.md`
- Read: `AI_context/06_open_questions.md`
- Read: `AI_context/08_master_plan.md`
- Read: `AI_context/09_frontend_improvement_plan.md`
- Read: `AI_context/10_frontend_worklog.md`
- Read: `AI_context/execution_reports/CDS_GOLD_001_RUN2_EXPLANATION_AND_NEXT_STEPS.md`
- Read: `docs/00_product_scope.md`, `docs/01_architecture.md`, `docs/11_pilot_uat_checklist.md`
- Create: `docs/superpowers/acceptance/2026-08-26-cds-questionnaire-acceptance.md`
- Modify: `AI_context/06_open_questions.md` only when a question is answered by evidence or an explicit product decision

**Interfaces:**
- Consumes: the questionnaire decisions already captured in the existing spec and the RUN 2 evidence report.
- Produces: one traceable acceptance matrix mapping each requested outcome to a route, API, model, test, and owner.

- [ ] **Step 1: Record the current evidence before changing behavior.**

  Record the already-passing checks: frontend lint, typecheck, build, workbench tests, route smoke, focused backend tests, `docker compose ps`, `/dashboard` HTTP 200, and `/api/v1/health/deep` HTTP 200. Record that authenticated browser QA still requires a valid local account.

- [ ] **Step 2: Write the acceptance matrix.**

  Include these rows: intake questions, save/resume, questionnaire-to-rule applicability, missing-information status, risk explanation, document-first workbench, provisional OCR confirmation, area mismatch, Fard date, historical tax, additional evidence re-evaluation, reviewer waiver proposal, checker approval, final decision, Bank Pack, email login, SSO, roles, audit, backups, TLS, and rollback.

- [ ] **Step 3: Resolve the role wording before implementation.**

  Keep Admin, Reviewer, and Viewer as the user-facing baseline selected in the questionnaire. Retain the existing `Approver` capability as a controlled checker role because the existing waiver and decision services reject self-approval; document how the company IdP maps its groups to these four canonical roles.

---

### Task 2: Finish the CDS-GOLD-001 facts and waiver path before building new UI

**Files:**
- Modify: `backend/app/services/extractors/document_facts.py`
- Modify: `backend/app/services/dossier_autofill.py` where document facts are persisted and candidates are created
- Modify: `backend/app/services/rule_engine.py` for explicit date/fact availability semantics
- Modify: `backend/rules/diligence_rules.yaml` only for the gold historical-tax evidence rule and its applicability
- Modify: `backend/app/services/export_bank_pack.py` only if the final finding/waiver data is omitted from the pack
- Test: `backend/tests/test_cds_gold_001_semantics.py`
- Test: `backend/tests/test_contextual_autofill.py`
- Test: `backend/tests/test_next_action.py`
- Test: `backend/tests/test_exception_waivable.py`
- Modify: `AI_context/02_findings.md`, `AI_context/04_worklog.md`, `AI_context/05_decisions.md`, `AI_context/06_open_questions.md`
- Create or update: `AI_context/execution_reports/05_cds_gold_001_run3.md`

**Interfaces:**
- Consumes: `DocumentFact`, `CaseContext`, `extract_document_facts`, `evaluate_rule`, existing approval services, and the RUN 2 corpus.
- Produces: reliable typed facts with document/page evidence, explicit `NeedsReview`/unknown behavior when dates or values are absent, and a reproducible RUN 3 report.

- [ ] **Step 1: Add failing tests for the missing gold facts.**

  Add tests proving that `extract_document_facts` extracts `4 Kanal` from a Sale Deed, extracts an explicit Fard issue date rather than using upload time, and detects historical-tax evidence as unavailable when only current clearance is present. Add a test that an unknown Sale Deed area does not trigger an area mismatch. Add a test that an unparseable Fard date produces a visible unconfirmed-date state rather than treating upload time as legal issue date.

- [ ] **Step 2: Run the focused tests and confirm the gaps.**

  Run from `backend`: `python -m pytest tests/test_cds_gold_001_semantics.py tests/test_contextual_autofill.py tests/test_next_action.py tests/test_exception_waivable.py -q`. Capture the failing assertions in the worklog; do not weaken the tests to match current behavior.

- [ ] **Step 3: Implement the smallest extraction changes.**

  Extend the existing document-fact patterns for Sale Deed area anchors and historical-tax wording. Preserve source document ID, page number, raw value, normalized value, and confidence. Keep area normalization in `area_to_marlas`. Make the rule evaluator require two known comparable values before triggering a mismatch. Make Fard freshness use an explicit extracted issue date; if absent, emit a reviewable “date unconfirmed” fact/status instead of substituting upload time.

- [ ] **Step 4: Add the historical-tax rule and preserve waiver semantics.**

  The rule must distinguish “current clearance is clean” from “historical evidence exists.” It should create an open finding when historical evidence is unavailable, permit a Reviewer/Admin waiver request with a reason, reject self-approval, and apply `Waived` only after the separate Approver/Admin decision. Preserve audit entries for proposal and decision.

- [ ] **Step 5: Run the tests and update AI_context evidence.**

  Run the focused tests again, then run the existing targeted/full backend suite used by the repo. Record exact counts, skipped tests, and any PyJWT environment issue in `AI_context/04_worklog.md`; update finding statuses in `AI_context/02_findings.md` and the decision rationale in `AI_context/05_decisions.md`.

- [ ] **Step 6: Execute and record clean RUN 3.**

  Use the RUN 2 corpus plus the remaining gold evidence. Verify initial findings: area mismatch, missing plan, dues, prior charge, name variation, stale/unconfirmed Fard, and historical tax as applicable. Upload the remediation batch and verify each intended resolution. Propose and approve the historical-tax waiver with different identities. Verify the final decision and Bank Pack reflect the exact state. Store IDs, timestamps, commands, and result summaries in `AI_context/execution_reports/05_cds_gold_001_run3.md`.

---

### Task 3: Implement the questionnaire-backed matter intake

**Files:**
- Create: `backend/alembic/versions/20260826_add_case_intake.py`
- Modify: `backend/app/models/case.py`
- Modify: `backend/app/schemas/case.py`
- Modify: `backend/app/api/routes/cases.py`
- Modify: `backend/app/services/dossier_autofill.py` only to reconcile explicit intake answers with inferred candidates
- Modify: `frontend/lib/api.ts`
- Create: `frontend/types/intake.ts`
- Create: `frontend/components/cases/matter-intake-form.tsx`
- Modify: `frontend/app/(dashboard)/dashboard/cases/page.tsx`
- Modify: `frontend/app/(dashboard)/dashboard/cases/[caseId]/page.tsx`
- Modify: `frontend/components/workbench/matter-workbench.tsx`
- Create: `backend/tests/test_case_intake.py`
- Create: `frontend/lib/intake.test.ts` or add assertions to the existing focused frontend harness

**Interfaces:**
- Consumes: current `CaseCreate`, case routes, current dossier fields, and existing required-evidence/rule applicability logic.
- Produces: `CaseIntake` data stored with the Case, an API-safe questionnaire payload, a save/resume form, and a visible “incomplete” state when required answers or evidence are missing.

- [ ] **Step 1: Define the intake contract before editing the form.**

  Add an explicit `intake_json` JSONB field or an equivalent migration-backed structure containing: `borrower_type` (`company` or `individual`), `transaction_type` (`mortgage`), `property_location`, `facility_amount`, `purpose`, `required_review_scope`, `expected_document_types`, and `review_notes`. Required fields must be explicit in Pydantic schemas; do not accept arbitrary keys.

- [ ] **Step 2: Write the failing API and validation tests.**

  Test create, read, and update of intake data; reject unsupported borrower/transaction values; ensure tenant scoping; ensure Viewer cannot mutate it; ensure a partial intake returns an incomplete status with missing field names; ensure explicit answers take precedence over inferred candidates only after reviewer confirmation.

- [ ] **Step 3: Add the migration and API support.**

  Add the model field and migration, extend `CaseCreate` with an optional typed intake object for backward compatibility, add a dedicated update endpoint if the existing case update route cannot safely carry partial intake, and include intake completeness in the case/workbench response. Run Alembic upgrade and the new backend tests before touching UI.

- [ ] **Step 4: Build a plain desktop questionnaire.**

  Replace the title-only New Case dialog with a short staged form: Matter identity, borrower/transaction, property/facility, evidence expectations, and review handoff. Include Save draft, Continue, Back, and Cancel. Show required fields and validation messages. Keep the form keyboard navigable and use existing semantic tokens and 44px controls.

- [ ] **Step 5: Connect the questionnaire to the workbench.**

  After creation, route to the Matter with the Documents-first layout. Show the answers in the Matter header/summary, show “Incomplete” with the exact missing answers/evidence, and allow Reviewer/Admin edits. Do not auto-assert legal conclusions from questionnaire answers.

- [ ] **Step 6: Verify backward compatibility.**

  Existing title-only case creation, existing seeded cases, Viewer read-only behavior, and old API clients must continue to work. Run frontend lint/typecheck/build, focused frontend tests, the route smoke test, and focused backend tests.

---

### Task 4: Finish the dashboard-to-Matter workbench flow

**Files:**
- Modify: `frontend/components/inbox/inbox-view.tsx`
- Modify: `frontend/components/app-sidebar.tsx`
- Modify: `frontend/components/workbench/matter-workbench.tsx`
- Modify: `frontend/components/workbench/file-pane.tsx`
- Modify: `frontend/components/workbench/evidence-pane.tsx`
- Modify: `frontend/components/workbench/evidence-viewer.tsx`
- Modify: `frontend/components/workbench/findings-list.tsx`
- Modify: `frontend/components/workbench/work-pane.tsx`
- Modify: `frontend/components/workbench/decision-strip.tsx`
- Modify: `frontend/components/cases/DocumentsPanel.tsx`, `ExceptionsPanel.tsx`, and `AuditPanel.tsx` only where the legacy route still exposes conflicting labels or actions
- Modify: `frontend/app/approvals/page.tsx`
- Modify: `frontend/app/(dashboard)/dashboard/cases/[caseId]/page.tsx`
- Test: `frontend/lib/workbench/run-unit-tests.ts` and focused component tests where a stable seam exists

**Interfaces:**
- Consumes: existing workbench API response, intake completeness, document facts, findings, approvals, and audit records.
- Produces: a predictable desktop flow: Dashboard queue → Matter → File/Evidence → Work finding → reviewer action → approval → Bank Pack.

- [ ] **Step 1: Write route/interaction acceptance tests.**

  Cover Dashboard links to mine/blocked/ready queues, Matter links to a selected document and page, finding selection, “request document,” provisional-value confirmation, waiver proposal, approval handoff, and Bank Pack access. Use existing route smoke infrastructure for unauthenticated redirects and add authenticated checks once a test account is available.

- [ ] **Step 2: Make Dashboard the operational entry point.**

  Keep the existing overview section but ensure each count is actionable, risk labels include explanations, incomplete matters expose the missing next action, and queue links preserve query state. Remove duplicate or decorative dashboard cards only when they duplicate the Inbox/Matter workflow.

- [ ] **Step 3: Make the Matter screen document-first.**

  Keep File/Evidence visible first, keep the summary beside it, and keep the selected page/document in URL query state. A finding must show severity, explanation, evidence requirement, source page references, status, and next action in one Work pane.

- [ ] **Step 4: Make uncertainty and missing evidence explicit.**

  Render provisional OCR/extraction values as provisional, require reviewer confirmation before persistence, and render missing required evidence as incomplete rather than as a successful empty state. Keep Exceptions and CP visually and semantically separate.

- [ ] **Step 5: Connect approval and Bank Pack actions.**

  Reviewers can prepare/submit; only the checker role can approve/reject. Show pending requests and rationale in Approvals, show the final decision in the Matter header, and link the generated Bank Pack to the same evidence/finding/waiver state.

- [ ] **Step 6: Run the browser verification pass.**

  With the local stack and a seeded authenticated account, inspect Dashboard, Cases, Matter, Documents, Exceptions, CP, Approvals, Audit, and Bank Pack in the in-app browser at desktop size. Record any visual or interaction defects in `AI_context/10_frontend_worklog.md`; do not mark visual QA complete from an unauthenticated login redirect alone.

---

### Task 5: Add company SSO while preserving email login and role boundaries

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/routes/auth.py`
- Create: `backend/app/services/oidc.py`
- Create: `backend/app/schemas/sso.py`
- Modify: `backend/app/models/user.py` only if an external subject/provider identity mapping is missing
- Create: `backend/alembic/versions/20260826_add_external_identity.py` if the model changes
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/auth/sso/callback/route.ts` or the equivalent server-side callback route
- Test: `backend/tests/test_auth_sso.py`
- Test: `backend/tests/test_rbac_smoke.py`
- Modify: `.env.example`, `.env.production.example`, `docs/ops/ENVIRONMENT_MATRIX.md`, `docs/ops/DEPLOYMENT_PROD.md`

**Interfaces:**
- Consumes: existing secure access-token cookie, `UserOrgRole`, `require_role`, audit logging, and the company’s OIDC metadata/client credentials.
- Produces: a generic OIDC authorization-code flow with validated issuer, audience, nonce/state, external-subject mapping, first-login policy, and audited login/failure events.

- [ ] **Step 1: Confirm the IdP contract before coding.**

  Obtain issuer URL, client ID, redirect URI, allowed email/domain or group policy, claim names for email/name/groups, logout URL, and whether the IdP returns a stable subject. Do not hard-code a vendor-specific assumption into the product.

- [ ] **Step 2: Write failing security tests.**

  Test state/nonce mismatch, issuer/audience mismatch, missing email, unknown external subject, disabled user, group-to-role mapping, tenant isolation, and successful callback. Test that SSO does not bypass the existing `must_change_password` or role checks.

- [ ] **Step 3: Implement server-side OIDC validation.**

  Keep tokens server-side during callback processing, validate discovery/JWK signatures and claims, map or provision the user according to an explicit policy, issue the existing access-token cookie, and write audit events. Never log raw ID tokens or authorization codes.

- [ ] **Step 4: Add the login choice.**

  Keep email/password as the default working path and add a clearly labeled company SSO button only when SSO configuration is present. Show actionable failure states without exposing provider secrets or raw claim payloads.

- [ ] **Step 5: Verify roles and checker separation.**

  Map Admin, Reviewer, Viewer, and the controlled Approver checker group. Run RBAC tests and an authenticated browser pass for login, dashboard access, read-only Viewer behavior, Reviewer submission, and Approver decision.

---

### Task 6: Prepare and validate private production deployment

**Files:**
- Read/modify: `docker-compose.prod.yml`
- Read/modify: `Caddyfile`
- Modify: `.env.production.example`
- Modify: `docs/ops/DEPLOYMENT_PROD.md`, `docs/ops/ENVIRONMENT_MATRIX.md`, `docs/ops/RELEASE_CHECKLIST.md`, `docs/ops/BACKUP_AND_RESTORE.md`
- Modify: `scripts/ops/preflight_prod.ps1` and backup scripts only when a documented gap is found
- Create: `docs/ops/CDS_PRIVATE_DEPLOYMENT_RUNBOOK.md`
- Create: `scripts/ops/verify_prod_readiness.ps1`

**Interfaces:**
- Consumes: existing production Compose services, Caddy TLS configuration, environment matrix, health endpoint, backup/restore scripts, and the selected host’s DNS/firewall/secrets.
- Produces: a repeatable private Linux/on-prem deployment and release checklist; it does not deploy without explicit host authorization.

- [ ] **Step 1: Run a read-only production configuration audit.**

  Check that all production services use the same `.env.production`, that no placeholder secret can pass preflight, that Caddy routes only intended public services, that MinIO is not unnecessarily exposed, and that health checks cover API, database, Redis, object storage, OCR, worker, frontend, and migration completion.

- [ ] **Step 2: Define the minimum host profile.**

  Record Linux distribution, Docker/Compose versions, CPU/RAM/disk headroom for the OCR image, private network placement, firewall ports 80/443 only, DNS, backup destination, operator account, and recovery owner. Keep Postgres, Redis, MinIO, OCR, and internal services on the private Compose network.

- [ ] **Step 3: Add the executable readiness check.**

  Make `verify_prod_readiness.ps1` validate required environment variables, reject placeholders and short secrets, render the Compose config, verify Caddy syntax/config mount, verify image build availability, and verify that the health endpoint and backup commands are defined. It must fail with a specific reason and never print “ready” after a failed check.

- [ ] **Step 4: Validate backup and restore before first deployment.**

  Run PostgreSQL and MinIO backups, restore into an isolated test volume/database, run migrations, and verify a known matter/document can be read. Record retention, encryption, access control, and restore time in the deployment runbook.

- [ ] **Step 5: Document the controlled release sequence.**

  The runbook must be: preflight → backup → pull/build images → migration → start services → health checks → TLS/domain check → authenticated smoke test → release record. Rollback is code rollback plus database/object-storage restore; do not promise an unsafe automatic downgrade.

- [ ] **Step 6: Stop at the authorization boundary.**

  Do not run the production Compose stack until the user supplies the selected host, domain, DNS/TLS ownership, production secret source, backup destination, and deployment authorization.

---

### Task 7: Final verification and handoff

**Files:**
- Modify: `AI_context/10_frontend_worklog.md`
- Modify: `AI_context/04_worklog.md`
- Modify: `docs/ops/RELEASE_CHECKLIST.md`
- Create: `docs/superpowers/acceptance/2026-08-26-cds-questionnaire-verification.md`

**Interfaces:**
- Consumes: all task outputs and the local/production verification commands.
- Produces: evidence-backed completion status with explicit remaining blockers.

- [ ] **Step 1: Run the complete local gate.**

  Run the startup contract test, frontend lint/typecheck/build/workbench tests/route smoke, focused backend tests, the full backend suite where the environment supports it, `git diff --check`, database migrations, `docker compose ps`, dashboard HTTP 200, API deep health HTTP 200, and the authenticated browser workflow.

- [ ] **Step 2: Run the gold acceptance workflow.**

  Verify RUN 3 initial findings, remediation, waiver, checker approval, final decision, and Bank Pack consistency. Update both the execution report and the acceptance matrix with exact evidence.

- [ ] **Step 3: Review unresolved blockers.**

  If `AI_context/06_open_questions.md` still has Q1 open, do not state an OCR accuracy result. If IdP or production host details are absent, state SSO/deployment as prepared but not activated.

- [ ] **Step 4: Handoff for implementation.**

  Implement in task order: Task 1 → Task 2 → Task 3 → Task 4, then Task 5 and Task 6 in parallel only after their external inputs are available. Use a fresh verification checkpoint after every task and keep each commit independently revertable.

---

## Self-review

### Spec coverage

- Dashboard overview, risk labels, missing information, and human review: Tasks 3–4.
- Document-first Matter workflow and provisional OCR evidence: Tasks 2–4.
- Questionnaire-specific UI and saved intake state: Task 3.
- Email login, SSO, and roles: Task 5.
- Reviewer/Approver waiver and final decision: Tasks 2 and 4.
- Private deployment, TLS, secrets, backups, and rollback: Task 6.
- AI_context measurement discipline and RUN 3: Tasks 1, 2, and 7.

### Known blockers

- Representative OCR samples and ground truth are still required before accuracy claims; see `AI_context/06_open_questions.md` Q1.
- SSO cannot be activated without the company IdP contract and redirect/domain details.
- Production deployment cannot be executed without an authorized private host, DNS/TLS ownership, secrets, and backup destination.
- Authenticated visual QA requires a valid local account; the in-app browser currently reaches the login redirect correctly but does not prove protected-route behavior by itself.
