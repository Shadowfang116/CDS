# CDS Local UI and Deployment Design

## Goal

Make the existing Covenant Diligence Systems workspace easier to operate on desktop, with the dashboard as the primary entry point, while preserving the human-review workflow for OCR, risks, exceptions, and approvals.

## Product decisions

- Primary audience: bank legal officers, credit officers, and external legal reviewers.
- First run: full local stack through Docker Compose.
- Deployment direction: prepare the existing Docker/Caddy setup; recommend hosting after inspecting its operational requirements.
- Access: email/password and company SSO, with Admin, Reviewer, and Viewer roles.
- Uncertain results: route to a human reviewer; never silently treat them as verified.
- Missing information: mark the matter incomplete and explain what is missing.
- Risk presentation: clear color, label, and short explanation.
- UI: desktop-first, clean, professional, and minimal.
- Main focus: dashboard overview of cases, documents, and pending reviewer tasks.
- Case workspace: documents first, summary at the side.

## Existing architecture to preserve

The repository already provides a Next.js App Router frontend, FastAPI backend, PostgreSQL, Redis, MinIO, Celery, OCR service, Docker Compose, and Caddy-oriented deployment files. The implementation should reuse existing routes, components, API contracts, and design tokens rather than introduce a parallel application shell.

## Acceptance criteria

1. The startup script exits non-zero when Docker or migrations fail and never prints that the stack is ready in that state.
2. The dashboard clearly presents open matters, risk levels, recent documents, and pending reviewer work.
3. Case review keeps source documents and evidence visible, marks provisional OCR values as provisional, and explains risk or missing information.
4. Existing roles, human approval, exceptions, CPs, audit history, and bank-pack states remain intact.
5. Frontend lint/typecheck and focused backend tests pass, or any environmental blocker is recorded with evidence.

## Out of scope

This pass does not invent a new legal conclusion engine, replace the existing OCR service, add a new authentication provider, or deploy to a public host without the required credentials and hosting choice.
