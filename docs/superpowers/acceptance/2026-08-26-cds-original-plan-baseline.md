# CDS Original Plan Baseline

Recorded during implementation start on 2026-08-26.

## Runtime

- Branch: `refactor/cds-backend-core`
- Docker Compose stack: running
- API: healthy on `http://localhost:8000`
- Frontend: healthy on `http://localhost:3000`
- OCR service: running on `http://localhost:8001`
- HF extractor: healthy on `http://localhost:8090`
- PostgreSQL, Redis, MinIO, worker, beat, and MailHog: healthy
- Dashboard probe: `http://localhost:3000/dashboard` returned HTTP 200
- Deep API health probe: `http://localhost:8000/api/v1/health/deep` returned HTTP 200
- Startup contract: `scripts/ci/test-start-services.ps1` passed

## Existing verification evidence

- Frontend lint, typecheck, build, workbench tests, and route smoke checks were previously recorded as passing in the frontend worklog.
- Focused backend tests for RBAC, document classification, exceptions, and next action were previously recorded as passing.
- `git diff --check` was previously recorded as clean for the existing implementation changes.

## Known blockers and boundaries

- Authenticated browser QA requires a valid local account; unauthenticated protected routes correctly redirect to login.
- `AI_context/06_open_questions.md` Q1 remains open: representative OCR samples and ground-truth text are not present, so no OCR accuracy percentage may be claimed.
- SSO is not configured because company identity-provider details are not present.
- Production deployment is not authorized; it requires a selected private Linux/on-prem host, domain/TLS ownership, production secrets, backup destination, and explicit authorization.

## Next implementation gate

Proceed with the dashboard/Matter review work using existing API data and role boundaries. Preserve the runtime and evidence constraints above.
