# Bank Diligence Platform (MVP)

## Objective
Convert property deal documents into:
- structured dossier
- Exceptions + CP list
- draft letters/undertakings/opinion skeleton (DOCX)
- Bank Pack export (PDF)
with audit logging + RBAC + on-prem deploy.

## Stack
- Frontend: Next.js
- Backend: FastAPI
- Worker: Celery
- DB: Postgres
- Queue: Redis
- Object storage: MinIO
- Deploy: Docker Compose

## Operating protocol (Cursor ↔ ChatGPT)
1) In Cursor: implement only what is requested in the current step.
2) When stuck: paste a Context Bundle into ChatGPT.
3) Require copy-paste-ready patches + commands + verification.

### Context Bundle template
```text
[GOAL]
...

[CURRENT STATE]
...

FILES
- path: ...
  ...

ERROR/LOGS
...

CONSTRAINTS
...
```

## Local dev

### Copy env
```bash
cp .env.example .env
```

### Start services
```bash
docker compose up --build
```

## MVP milestones

- D1: Auth + orgs + roles + audit log
- D2: Upload + MinIO storage
- D3: OCR + classification + extraction + dossier confirm
- D4: Rules engine + exceptions/CP UI
- D5: Drafts + bank pack export
- D6: Security + on-prem pilot pack

