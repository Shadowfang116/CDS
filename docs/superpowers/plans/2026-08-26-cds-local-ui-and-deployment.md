# CDS Local UI and Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing CDS desktop workflow clearer, make local startup truthful, and prepare the existing containerized deployment path for a hosting recommendation.

**Architecture:** Reuse the current Next.js shell, dashboard, case workspace, document viewer, and API contracts. Make the smallest changes at the presentation and startup boundaries; do not fork the product flow or change legal-review semantics.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS, FastAPI, Docker Compose, PowerShell.

**Spec:** `docs/superpowers/specs/2026-08-26-cds-local-ui-and-deployment-design.md`

## Global Constraints

- Preserve the CDS name and Pakistan property-diligence terminology.
- Keep OCR and extraction provisional until a human confirms them.
- Keep Exceptions separate from Conditions Precedent.
- Keep desktop-first layout; do not add mobile-specific scope.
- Preserve unrelated user changes already present in the worktree.
- Do not claim Docker services are running when Docker is unavailable or migrations fail.

---

### Task 1: Make local startup fail truthfully

**Files:**
- Modify: `start-services.ps1`

**Interfaces:**
- Produces: a non-zero exit code when compose startup or migrations fail, and readiness output only after both succeed.

- [ ] Add explicit checks after `docker compose up -d --build` and `docker compose exec -T api alembic upgrade head` using `$LASTEXITCODE`.
- [ ] Print a concise recovery message that names Docker Desktop/Linux engine or migration failure as appropriate.
- [ ] Run the script with Docker unavailable and confirm it exits non-zero without printing `Local stack is up.`.

### Task 2: Inspect and baseline the existing frontend

**Files:**
- Read: `frontend/app/dashboard/page.tsx`
- Read: `frontend/components/inbox/inbox-view.tsx`
- Read: `frontend/components/app-sidebar.tsx`
- Read: `frontend/components/cases/case-workspace.tsx`
- Read: `frontend/components/documents/DocumentViewer.tsx`
- Read: `frontend/app/globals.css`

**Interfaces:**
- Produces: a verified list of existing dashboard, navigation, case, document, and risk UI surfaces to adjust without duplicating functionality.

- [ ] Trace the dashboard data flow from `frontend/app/dashboard/page.tsx` into the inbox view and its API calls.
- [ ] Identify the existing risk, exception, missing-document, and provisional-extraction components.
- [ ] Record the current test commands from `frontend/package.json` and the backend test layout.

### Task 3: Improve dashboard hierarchy and desktop readability

**Files:**
- Modify: existing dashboard/inbox components identified in Task 2.
- Modify: `frontend/app/globals.css` only where existing tokens or layout rules are responsible.
- Test: existing frontend smoke/typecheck coverage; add focused component coverage only if a stable test seam exists.

**Interfaces:**
- Consumes: current dashboard API data and role-aware shell.
- Produces: a desktop dashboard that leads with open matters and risk, then recent documents and pending reviewer work.

- [ ] Add or reorder visible sections using existing data models rather than mocked values.
- [ ] Use restrained borders, spacing, and typography; avoid decorative gradients, oversized cards, and non-functional badges.
- [ ] Ensure each risk state has a readable label and short explanation, not color alone.
- [ ] Ensure empty, loading, and error states remain understandable.

### Task 4: Improve navigation and case workspace focus

**Files:**
- Modify: `frontend/components/app-sidebar.tsx`
- Modify: `frontend/components/cases/case-workspace.tsx`
- Modify: `frontend/components/documents/DocumentViewer.tsx` only where it affects the requested document-first layout.

**Interfaces:**
- Consumes: existing routes and case/document data.
- Produces: predictable desktop navigation and a case screen with documents first and summary alongside.

- [ ] Keep navigation labels aligned with matter, dossier, exception, CP, audit, and bank-pack terminology.
- [ ] Make the active route and reviewer next action easy to identify.
- [ ] Keep document evidence and page references close to extracted fields and risk explanations.
- [ ] Preserve confirmation affordances for provisional OCR values.

### Task 5: Verify the workflow and deployment readiness

**Files:**
- Read: `docker-compose.yml`, `docker-compose.prod.yml`, `Caddyfile`, `DEPLOYMENT.md`, `docs/ops/DEPLOYMENT_PROD.md`.
- Run: frontend and focused backend checks.

**Interfaces:**
- Produces: evidence-backed local verification results and a hosting recommendation based on the current container boundaries.

- [ ] Run frontend lint, typecheck, and route smoke checks where dependencies permit.
- [ ] Run focused backend tests covering RBAC, document classification, OCR, exceptions, and next action.
- [ ] Re-run the startup probe and record Docker Desktop as an external prerequisite if its engine remains stopped.
- [ ] Review production compose/Caddy/env requirements and state the minimum hosting profile; do not deploy without explicit credentials and a selected host.

## Self-review

- Spec coverage: startup truthfulness is Task 1, UI hierarchy is Tasks 3–4, workflow preservation is Tasks 2–4, and verification/deployment preparation is Task 5.
- Placeholder scan: no TBD/TODO/FIXME steps are used.
- Scope: the plan intentionally avoids changing authentication providers, OCR engines, or legal rules.
