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

## End-to-end testing checklist

### Prerequisites: Reset + Seed + Build

```powershell
# 1. Reset database and seed demo data
.\scripts\dev\pilot_reset.ps1

# 2. Rebuild frontend and API (force recreate to ensure latest changes)
docker compose up -d --build --force-recreate frontend api

# Note: If Docker build shows "CACHED" unexpectedly, run:
docker compose build --no-cache frontend
```

### URLs
- **Frontend Dashboard:** http://localhost:3000/dashboard
- **API Documentation (Swagger):** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/api/v1/health/deep

### Login credentials
- **OrgA Admin:** admin@orga.com (any password)
- **OrgA Reviewer:** reviewer@orga.com (any password)
- **OrgB Admin:** admin@orgb.com (any password)

### Manual testing steps

1. **Login and navigate to dashboard**
   - Open http://localhost:3000/dashboard
   - Login with admin@orga.com
   - Verify dashboard loads without CORS errors (check browser console)
   - **CRITICAL:** Open DevTools Network tab and verify:
     - Requests go to `http://localhost:3000/api/v1/*` (same-origin, NOT `:8000`)
     - No endless stream of requests (should see < ~20 total requests)
     - No "Loading..." flashing loop

2. **Open demo case (Network stability test)**
   - Click on "PILOT DEMO CASE" from the cases list
   - **CRITICAL:** Watch Network tab - should see:
     - Initial burst of 3-5 requests (case, documents, controls)
     - Requests then STOP (no continuous growth)
     - Total requests remain stable (< ~20)
   - Verify case page loads completely without flashing
   - Verify all sections render (Documents, Dossier, Exceptions, CPs, etc.)

3. **Document viewer**
   - Open a document (e.g., PILOT_DEMO_DOCUMENT.pdf)
   - Verify document viewer loads pages
   - Verify OCR text is visible (should show text from seeded data)

4. **OCR extraction review**
   - Navigate to Dossier section
   - Click "Extract from OCR" button
   - **Expected:** Either:
     - See at least one extraction candidate with "Edit" / "Confirm" buttons, OR
     - See a clear empty-state message: "No pending OCR extractions found..."
   - If candidate exists: Click "Edit" to modify value, then "Confirm" to apply

5. **Generate exports**
   - Navigate to Exports section
   - Click "Generate Bank Pack"
   - Verify export is created and appears in the list
   - Click download link and verify PDF downloads (should use same-origin proxy)

6. **Integrations page (Admin only test)**
   - Navigate to Integrations page
   - If logged in as Admin: Email Deliveries section should load
   - If logged in as non-Admin: Should show friendly "Admin only" message (no crash)

7. **Verify audit log**
   - Check that actions are logged (view case, extract OCR, generate export, etc.)
   - Audit entries should appear in the activity feed

### Verification commands

```powershell
# Verify backend routes are configured correctly
.\scripts\dev\verify_backend_routes.ps1

# Run automated smoke tests (should pass 35/35)
.\scripts\dev\smoke_test.ps1
```

### Troubleshooting

- **CORS errors in browser console:** Ensure frontend is using same-origin proxy (`/api/v1/*`), not direct `http://localhost:8000` calls
- **"Loading..." flashing / infinite requests:** 
  - Check browser Network tab - requests should go to `http://localhost:3000/api/v1/*`, not `:8000`
  - If you see hundreds/thousands of repeated requests, check browser console for `fetchApi` trace logs (dev mode only)
  - Ensure case page loads only once per case ID change
  - Request de-duplication should prevent concurrent identical GET requests
- **No OCR extraction candidates:** Run `.\scripts\dev\pilot_reset.ps1` again to ensure demo candidate is created
- **Required documents missing:** Re-run `.\scripts\dev\pilot_reset.ps1` to re-seed data

## MVP milestones

- D1: Auth + orgs + roles + audit log
- D2: Upload + MinIO storage
- D3: OCR + classification + extraction + dossier confirm
- D4: Rules engine + exceptions/CP UI
- D5: Drafts + bank pack export
- D6: Security + on-prem pilot pack

