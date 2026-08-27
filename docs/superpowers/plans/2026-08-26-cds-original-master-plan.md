# CDS Original Master Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved CDS plan into a verified desktop workflow: a clear dashboard, reliable document and risk review, human approval controls, and deployment readiness.

**Architecture:** Reuse the existing Next.js dashboard shell, Inbox, Matter workbench, document viewer, FastAPI APIs, OCR service, rule engine, approval services, and Docker/Caddy deployment files. Make focused changes at the existing presentation and workflow boundaries; do not create a second product flow or replace the current legal-review semantics.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS, GSAP core utilities, FastAPI, SQLAlchemy, PostgreSQL, Celery, Redis, MinIO, OCR microservice, Docker Compose, Caddy, pytest, PowerShell.

**Spec:** `docs/superpowers/specs/2026-08-26-cds-local-ui-and-deployment-design.md`

## Global Constraints

- Support Admin, Reviewer, and Viewer audiences; preserve the existing Approver checker capability for maker-checker actions.
- Keep the desktop-first scope and the clean, professional, simple/minimal visual direction.
- Make Dashboard the main entry point and show cases, documents, and reviewer tasks together.
- Keep Case/Matter review documents-first with the summary beside the evidence.
- Treat OCR and extraction as provisional until a human confirms them.
- Mark missing information as incomplete and state what is missing.
- Show risk with a clear severity label, color, and short explanation; never rely on color alone.
- Keep Exceptions separate from Conditions Precedent.
- Preserve tenant scoping, role checks, audit logging, and approval separation.
- Do not claim OCR accuracy until representative samples and ground truth exist and are measured in `AI_context/04_worklog.md`.
- Preserve unrelated existing worktree changes.
- Do not deploy publicly without an explicitly selected private host, domain, TLS ownership, production secrets, backup location, and authorization.

## Approved Scope Mapped to Repository Files

| Approved outcome | Existing implementation boundary |
|---|---|
| Start local system | `start-services.ps1`, `docker-compose.yml`, Docker health checks |
| Dashboard first | `frontend/app/dashboard/page.tsx`, `frontend/components/inbox/inbox-view.tsx`, `frontend/components/dashboard/` |
| Navigation | `frontend/components/app-sidebar.tsx`, `frontend/app/(dashboard)/layout.tsx` |
| Case details/documents first | `frontend/components/workbench/matter-workbench.tsx`, `frontend/components/workbench/file-pane.tsx`, `frontend/components/workbench/evidence-pane.tsx`, `frontend/components/documents/DocumentViewer.tsx` |
| Risks/missing information | `frontend/components/workbench/findings-list.tsx`, `frontend/components/workbench/work-pane.tsx`, `frontend/components/cases/ExceptionsPanel.tsx`, `backend/app/services/rule_engine.py` |
| OCR/classification | `ocr_service/`, `backend/app/services/canonical_docs.py`, `backend/app/services/doc_classifier.py`, `backend/app/services/extractors/` |
| Human review/approval | `backend/app/services/approvals.py`, `backend/app/api/routes/approvals.py`, `frontend/app/approvals/page.tsx` |
| Login/roles | `backend/app/api/routes/auth.py`, `backend/app/core/roles.py`, `frontend/app/login/page.tsx` |
| Deployment | `docker-compose.prod.yml`, `Caddyfile`, `.env.production.example`, `docs/ops/`, `scripts/ops/` |

## Definition of Done

The original plan is complete when:

1. The local stack starts truthfully, migrations run, and every service is healthy.
2. Dashboard provides an actionable overview of cases, documents, pending reviewer work, risk, and incomplete matters.
3. Navigation leads predictably from Dashboard to Matter, evidence, work items, approvals, audit, and Bank Pack.
4. The Matter screen keeps documents and evidence primary, with summary, risk explanation, and next action beside them.
5. Upload → OCR → classification → extraction → risk/missing-information checks → reviewer confirmation → approval is verified on real seeded workflow data.
6. Reviewers can prepare and submit; only the checker role can approve waivers or final decisions; all actions are audited.
7. Frontend and backend verification commands pass, and authenticated browser QA is recorded.
8. Production deployment is prepared for the recommended private Linux VM/on-prem host, with secrets, TLS, backups, health checks, and rollback documented.

---

### Task 1: Establish the baseline and local runtime gate

**Files:**
- Read: `AI_context/README.md`, `AI_context/02_findings.md`, `AI_context/08_master_plan.md`, `AI_context/09_frontend_improvement_plan.md`, `AI_context/10_frontend_worklog.md`
- Read: `docker-compose.yml`, `start-services.ps1`, `README.md`, `docs/01_architecture.md`
- Modify: `start-services.ps1` only if the current failure handling regresses
- Test: `scripts/ci/test-start-services.ps1`
- Create: `docs/superpowers/acceptance/2026-08-26-cds-original-plan-baseline.md`

**Interfaces:**
- Consumes: existing Compose services and current verification commands.
- Produces: a reproducible local baseline and a written list of known blockers.

- [ ] **Step 1: Verify the local prerequisites.**

  Check Docker Desktop’s Linux engine, available disk/RAM, the working directory, required environment files, and the current Git worktree. Do not delete or reset unrelated changes.

- [ ] **Step 2: Run the startup contract test first.**

  Run `powershell -ExecutionPolicy Bypass -File scripts/ci/test-start-services.ps1`. Confirm the script checks both Compose startup and Alembic migration exit codes and does not print success after failure.

- [ ] **Step 3: Start the local system.**

  Run `powershell -ExecutionPolicy Bypass -File start-services.ps1`. If Docker is unavailable, stop with the exact recovery message; do not bypass the prerequisite or claim the stack is running.

- [ ] **Step 4: Verify service health.**

  Run `docker compose ps`, `Invoke-WebRequest http://localhost:3000/dashboard -UseBasicParsing`, and `Invoke-WebRequest http://localhost:8000/api/v1/health/deep -UseBasicParsing`. Record service status, HTTP codes, and any expected startup warnings.

- [ ] **Step 5: Record the baseline.**

  Capture the current route list, existing tests, current Docker services, and the known OCR limitation from `AI_context/06_open_questions.md` Q1. Save the result in the acceptance baseline document.

---

### Task 2: Complete the dashboard and desktop UI fixes

**Files:**
- Modify: `frontend/components/inbox/inbox-view.tsx`
- Modify: `frontend/components/dashboard/DashboardAnalyticsSection.tsx`, `frontend/components/dashboard/DrilldownDrawer.tsx`, and `frontend/components/dashboard/Charts.tsx` only where they duplicate or obscure the operational queue
- Modify: `frontend/components/app-sidebar.tsx`
- Modify: `frontend/components/dashboard-topbar.tsx`
- Modify: `frontend/app/globals.css` only for existing semantic tokens/layout rules
- Read: `frontend/components/layout/dashboard-motion.tsx`, `frontend/components/layout/dashboard-cursor.tsx`, `frontend/lib/gsap.ts`
- Test: `frontend/lib/workbench/run-unit-tests.ts`, `frontend/scripts/smoke-routes.mjs`, and existing frontend checks

**Interfaces:**
- Consumes: existing Inbox API response, role-aware shell, dashboard analytics, and current semantic design tokens.
- Produces: a clean desktop Dashboard that prioritizes open work and gives every summary value an actionable destination.

- [ ] **Step 1: Define the dashboard acceptance states.**

  Cover loading, unavailable API, empty queue, normal queue, high-risk matter, incomplete matter, pending reviewer task, Viewer access, and Reviewer/Admin actions. Use the existing API response; do not add mocked dashboard data.

- [ ] **Step 2: Make the hierarchy operational.**

  Lead with Needs me, Blocked/incomplete, Ready, and current high-risk work. Keep the overview of cases, documents, and reviewer tasks visible. Ensure every count links to a filtered queue or Matter.

- [ ] **Step 3: Improve risk and missing-information language.**

  Each risk state must show severity, a short explanation, and the next action. Missing information must say which document or reviewer action is needed. Preserve the red/clear warning direction selected in the UI decisions without using red as the only signal.

- [ ] **Step 4: Simplify navigation.**

  Align sidebar labels and active states with Dashboard, Cases/Matters, Documents, Exceptions, CP, Approvals, Audit, and Bank Pack. Remove ambiguous duplicate destinations only after confirming their routes are covered by the existing shell.

- [ ] **Step 5: Keep motion subordinate to review work.**

  Use only the existing GSAP core helpers for reveal/cursor polish. Do not add plugin-based motion or large visual effects; confirm `prefers-reduced-motion` behavior remains intact.

- [ ] **Step 6: Verify the UI.**

  Run `npm run lint`, `npm run typecheck`, `npm run test:workbench`, `npm run build`, and `npm run smoke:routes` from `frontend`. Record visual QA defects in `AI_context/10_frontend_worklog.md`.

---

### Task 3: Finish the document-first Matter and risk review workflow

**Files:**
- Modify: `frontend/components/workbench/matter-workbench.tsx`
- Modify: `frontend/components/workbench/file-pane.tsx`
- Modify: `frontend/components/workbench/evidence-pane.tsx`
- Modify: `frontend/components/workbench/evidence-viewer.tsx`
- Modify: `frontend/components/workbench/findings-list.tsx`
- Modify: `frontend/components/workbench/work-pane.tsx`
- Modify: `frontend/components/workbench/decision-strip.tsx`
- Modify: `frontend/components/documents/DocumentViewer.tsx` only for evidence/provisional-value presentation
- Modify: `frontend/components/cases/DocumentsPanel.tsx`, `ExceptionsPanel.tsx`, and `AuditPanel.tsx` only where the legacy route conflicts with the workbench
- Modify: `frontend/app/(dashboard)/dashboard/cases/[caseId]/page.tsx`
- Read: `frontend/lib/workbench/required-evidence.ts`, `frontend/lib/workbench/findings.ts`, `frontend/lib/workbench/next-action.ts`, `frontend/lib/workbench/submit-gate.ts`
- Test: `frontend/lib/workbench/run-unit-tests.ts` and focused tests for new stable seams

**Interfaces:**
- Consumes: current workbench API, document/page query state, findings, required evidence, provisional OCR values, approvals, and audit records.
- Produces: a desktop Matter page with documents first, summary beside them, and a single understandable path to the next reviewer action.

- [ ] **Step 1: Test document/page continuity.**

  Verify required-evidence rows open the preferred document and page, viewer navigation preserves the selected document/page in the URL, and returning from a finding keeps the same evidence context.

- [ ] **Step 2: Make the three work areas explicit.**

  Keep File for document completeness, Evidence for source text/page proof, and Work for findings, required evidence, risk explanation, and next action. Do not collapse Exceptions into CP.

- [ ] **Step 3: Surface provisional extraction correctly.**

  Label OCR/extracted values as provisional, show source document/page, expose confidence or uncertainty where available, and require Reviewer/Admin confirmation before the value becomes the accepted audited value.

- [ ] **Step 4: Make incomplete state actionable.**

  A missing required document, missing page reference, or unresolved low-confidence field must show Incomplete/Needs review with the exact action: upload, verify, correct, or request evidence.

- [ ] **Step 5: Connect finding resolution and approval.**

  A resolved finding must show the evidence that resolved it. A waived finding must show the reason, proposer, checker, decision time, and audit link. A final decision must be blocked when hard-stop exceptions or required CP items remain open.

- [ ] **Step 6: Verify the Matter workflow in the browser.**

  With an authenticated local account, inspect Dashboard → Matter → document → page → finding → evidence action → approval → Bank Pack at desktop size. Record screenshots or reproducible defects in the frontend worklog.

---

### Task 4: Verify and close the OCR/classification/risk workflow gaps

**Files:**
- Modify: `ocr_service/engines/tesseract_engine.py` and `ocr_service/engines/surya_engine.py` only when a measured finding requires it
- Modify: `ocr_service/preprocessing.py` only with before/after evidence
- Modify: `ocr_service/main.py`, `ocr_service/schemas.py`, and `ocr_service/quality.py` only when the served OCR contract needs it
- Modify: `backend/app/services/extractors/document_facts.py`
- Modify: `backend/app/services/dossier_autofill.py`
- Modify: `backend/app/services/rule_engine.py`
- Modify: `backend/rules/diligence_rules.yaml` only for verified applicability/fact gaps
- Test: `backend/tests/test_cds_gold_001_semantics.py`, `test_doc_classification.py`, `test_contextual_autofill.py`, `test_exception_waivable.py`, `test_next_action.py`
- Modify: `AI_context/02_findings.md`, `AI_context/04_worklog.md`, `AI_context/05_decisions.md`
- Create/update: `AI_context/execution_reports/05_cds_gold_001_run3.md`

**Interfaces:**
- Consumes: the production `ocr_service/` path, canonical document classification, document facts, rule engine, and existing RUN 2 evidence.
- Produces: measured, human-reviewable document understanding and a complete gold workflow result.

- [ ] **Step 1: Verify the served OCR path before changing engines.**

  Inspect `docker compose logs ocr_service` and call the service health/ocr endpoints. Confirm the requested engine and actual `engine_used` are visible. Do not prioritize Surya or an ensemble without a measured baseline.

- [ ] **Step 2: Add failing regression tests for RUN 2 gaps.**

  Cover Sale Deed area extraction, cross-document area comparison, explicit Fard issue date, historical-tax evidence availability, and unknown-fact behavior. Unknown values must not create invented legal findings.

- [ ] **Step 3: Implement the narrowest fact/rule fixes.**

  Preserve document ID, page, raw value, normalized value, and confidence. Require known comparable values for area mismatch. Treat missing Fard issue date as unconfirmed. Distinguish current tax clearance from historical tax evidence.

- [ ] **Step 4: Run the gold remediation sequence.**

  Initial batch should exercise the meaningful RUN 2 findings plus the remaining gold gaps. Additional evidence should resolve plan, dues, charge, identity, area, and freshness findings; historical tax should remain open until Reviewer proposal and separate checker approval.

- [ ] **Step 5: Record the evidence.**

  Update the AI_context finding table, worklog, decisions, and RUN 3 report in the same session. If samples are unavailable, record that OCR accuracy remains unmeasured rather than inventing a percentage.

---

### Task 5: Verify authentication, roles, human review, and approval

**Files:**
- Read/modify: `backend/app/api/routes/auth.py`
- Read/modify: `backend/app/core/roles.py`, `backend/app/api/deps.py`, `backend/app/models/user.py`
- Read/modify: `backend/app/services/approvals.py`, `backend/app/api/routes/approvals.py`
- Read/modify: `frontend/app/login/page.tsx`, `frontend/app/approvals/page.tsx`, `frontend/lib/use-me-role.ts`
- Test: `backend/tests/test_rbac_smoke.py`, `backend/tests/test_dual_control.py`, `backend/tests/test_exception_waivable.py`
- Create/update: an authenticated browser smoke procedure under `docs/11_pilot_uat_checklist.md` or `docs/ops/RELEASE_CHECKLIST.md`

**Interfaces:**
- Consumes: email/password login, JWT cookie, canonical roles, approval request types, audit logging, and existing role-aware UI.
- Produces: evidence that each selected audience can only perform its permitted actions.

- [ ] **Step 1: Verify email login and session behavior.**

  Test successful login, invalid credentials, lockout behavior, logout, expired/invalid cookie, forced password change, and protected-route redirect. Do not weaken authentication to make browser testing easier.

- [ ] **Step 2: Verify role boundaries.**

  Admin can manage users/configuration; Reviewer can prepare, correct, request evidence, and submit; Viewer can inspect but not mutate; Approver/Admin can perform checker decisions. Confirm tenant isolation for every role.

- [ ] **Step 3: Verify human review gates.**

  Confirm uncertain OCR values cannot be silently accepted, missing information blocks readiness, waiver requires a reason, the requester cannot self-approve, and every action creates an audit record.

- [ ] **Step 4: Decide SSO readiness separately from local authentication.**

  Keep email login working. Document SSO as a separate production configuration item until the company provides IdP issuer, client ID, redirect URI, claims/group mapping, domain, and secret-management details. Do not add guessed SSO settings.

---

### Task 6: Prepare deployment using the existing Docker/Caddy setup

**Files:**
- Read/modify: `docker-compose.prod.yml`
- Read/modify: `Caddyfile`
- Read/modify: `.env.production.example`
- Read/modify: `DEPLOYMENT.md`, `docs/DEPLOYMENT.md`, `docs/ops/DEPLOYMENT_PROD.md`, `docs/ops/ENVIRONMENT_MATRIX.md`
- Read/modify: `scripts/ops/preflight_prod.ps1`
- Read/modify: `scripts/ops/backup_postgres.ps1`, `scripts/ops/backup_minio.ps1`, `scripts/ops/restore_postgres.ps1`, `scripts/ops/restore_minio.ps1`
- Create: `docs/ops/CDS_PRIVATE_HOSTING_RUNBOOK.md`
- Create: `scripts/ops/verify_prod_readiness.ps1`

**Interfaces:**
- Consumes: the existing production Compose services, Caddy reverse proxy, environment matrix, health endpoint, and backup scripts.
- Produces: a private Linux VM/on-prem deployment package and a clear go/no-go checklist.

- [ ] **Step 1: Confirm the hosting recommendation from repository requirements.**

  Recommend a bank-controlled private Linux VM or on-prem server because the stack includes PostgreSQL, MinIO, OCR, audit data, private documents, and internal approval workflows. Treat public cloud as a later option requiring a security review, managed database/object storage design, and explicit bank approval.

- [ ] **Step 2: Audit production Compose and Caddy.**

  Ensure only Caddy exposes public HTTP/HTTPS, internal services stay on the private network, production uses `.env.production`, migrations run before API/worker readiness, and health checks cover all required dependencies.

- [ ] **Step 3: Harden the environment checklist.**

  Require non-placeholder `APP_SECRET_KEY`, database password, MinIO password, integration encryption key when used, correct `CORS_ORIGINS`, `PUBLIC_URL`, `PUBLIC_HOSTNAME`, SMTP settings, and external MinIO endpoint behavior for browser downloads.

- [ ] **Step 4: Add readiness verification.**

  `verify_prod_readiness.ps1` must validate required variables, reject placeholders/short secrets, render the Compose config, check Caddy configuration, verify image availability, and fail with a specific reason. It must never print a ready result after a failed check.

- [ ] **Step 5: Validate backup and restore.**

  Back up PostgreSQL and MinIO, restore into isolated targets, run migrations, verify a known Matter/document, and record retention, encryption, restore time, and responsible operator.

- [ ] **Step 6: Stop before real deployment authorization.**

  Do not run production deployment until the user supplies the selected host, domain/DNS ownership, TLS plan, production secret source, backup destination, and explicit authorization.

---

### Task 7: Final verification and release handoff

**Files:**
- Modify: `AI_context/10_frontend_worklog.md`, `AI_context/04_worklog.md`
- Modify: `docs/11_pilot_uat_checklist.md`, `docs/ops/RELEASE_CHECKLIST.md`
- Create: `docs/superpowers/acceptance/2026-08-26-cds-original-plan-verification.md`

**Interfaces:**
- Consumes: all task outputs, local Docker runtime, authenticated browser session, test accounts, and deployment checklist.
- Produces: a final evidence-backed status report.

- [ ] **Step 1: Run the local gates.**

  Run the startup contract test, frontend lint/typecheck/build/workbench tests/route smoke, focused backend tests, the complete backend suite where supported, `git diff --check`, migrations, `docker compose ps`, Dashboard HTTP 200, and API deep health HTTP 200.

- [ ] **Step 2: Run the authenticated workflow.**

  Verify login → Dashboard → Cases → Matter → upload → OCR/classification → findings → missing-information action → human confirmation → approval → Bank Pack → audit.

- [ ] **Step 3: Review all release blockers.**

  Keep OCR accuracy unclaimed if Q1 samples are absent. Keep SSO marked configuration-pending without IdP details. Keep production deployment marked authorization-pending without the host and secret/backup inputs.

- [ ] **Step 4: Update the final records.**

  Record exact commands, pass/fail results, screenshots or browser observations, known warnings, and the remaining owner for each blocked item. Do not mark the plan complete based only on a successful build.

---

## Recommended Hosting Decision

Based on `DEPLOYMENT.md`, `docker-compose.prod.yml`, `docs/ops/ENVIRONMENT_MATRIX.md`, and the document/audit workflow, the best first deployment target is:

**A bank-controlled private Linux VM or on-prem server running Docker Compose behind Caddy.**

Minimum profile:

- Linux host with Docker Engine and Compose
- Firewall exposing only 80/443 through Caddy
- Private PostgreSQL, Redis, MinIO, OCR, worker, and API services
- Persistent encrypted storage for PostgreSQL and MinIO
- Scheduled off-host backups and a tested restore path
- Bank-controlled DNS/TLS and production secret storage
- Sufficient CPU/RAM/disk for the OCR image and document workload

Do not select a public cloud deployment until the bank approves the data residency, document storage, key management, backup, and network model.

## Self-review

Every original approved item is covered:

- Local startup: Tasks 1 and 7.
- Dashboard/UI fixes: Task 2.
- Navigation and case details: Task 3.
- Cases/documents/reviewer tasks overview: Tasks 2 and 3.
- OCR/classification/risk/missing information: Task 4.
- Human review and approval: Tasks 3 and 5.
- Login and roles: Task 5.
- Tests: Tasks 1, 2, 4, 5, and 7.
- Docker/Caddy deployment and hosting recommendation: Task 6.

The plan intentionally does not add a separate questionnaire product feature; the earlier MCQ questionnaire is treated as the source of the approved requirements above.
