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

### Developer scripts (Windows PowerShell)

```powershell
# Full reset and seed demo data
.\scripts\dev\pilot_reset.ps1

# Run smoke tests
.\scripts\dev\smoke_test.ps1

# Verify backend route configurations
.\scripts\dev\verify_backend_routes.ps1
```

#### Manual verification one-liners (PowerShell-safe)

These commands use multiple `-e` patterns (no regex pipes). For simple checks, use direct grep:

```powershell
# A) Verification endpoint (evidence gate + Body parsing)
docker compose exec -T api grep -n -e MarkVerifiedRequest -e force -e evidence -e Body app/api/routes/verification.py

# B) OCR correction routes (api_route with PUT+POST)
docker compose exec -T api grep -n -e api_route -e ocr-text/correction -e PUT -e POST app/api/routes/ocr_text_corrections.py

# C) LibreOffice configuration
docker compose exec -T api grep -n -e UserInstallation -e lo-profile -e nolockcheck -e nodefault -e norestore -e HOME app/services/doc_convert.py
```

For robust checking that properly handles grep exit codes even when piping to head, use the sh wrapper pattern:

```powershell
# A) Verification endpoint (evidence gate + Body parsing)
docker compose exec -T api sh -lc 'out="$(grep -n -e MarkVerifiedRequest -e force -e evidence -e Body app/api/routes/verification.py || true)"; echo "$out" | head -n 20; [ -n "$out" ]'

# B) OCR correction routes (api_route with PUT+POST)
docker compose exec -T api sh -lc 'out="$(grep -n -e api_route -e ocr-text/correction -e PUT -e POST app/api/routes/ocr_text_corrections.py || true)"; echo "$out" | head -n 20; [ -n "$out" ]'

# C) LibreOffice configuration
docker compose exec -T api sh -lc 'out="$(grep -n -e UserInstallation -e lo-profile -e nolockcheck -e nodefault -e norestore -e HOME app/services/doc_convert.py || true)"; echo "$out" | head -n 20; [ -n "$out" ]'
```

Exit code 0 = matches found, 1 = no matches. For automated pass/fail checking with proper output formatting, use `.\scripts\dev\verify_backend_routes.ps1`.

## MVP milestones

- D1: Auth + orgs + roles + audit log
- D2: Upload + MinIO storage
- D3: OCR + classification + extraction + dossier confirm
- D4: Rules engine + exceptions/CP UI
- D5: Drafts + bank pack export
- D6: Security + on-prem pilot pack

