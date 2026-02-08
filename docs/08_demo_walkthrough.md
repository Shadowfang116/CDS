# Demo Walkthrough - Bank Diligence Platform

## PILOT QUICKSTART

**For non-technical stakeholders - One-command setup:**

### Step 1: Reset and Setup (Run Once)
```powershell
.\scripts\dev\pilot_reset.ps1
```

This will:
- Build and start all services (API, worker, frontend, database, etc.)
- Run database migrations
- Seed demo data (OrgA + OrgB with cases, documents, users)
- Print access URLs and login credentials

**Expected output:** All services running, demo data seeded, credentials printed.

### Step 2: Run Smoke Tests (Verify Everything Works)
```powershell
.\scripts\dev\smoke_test.ps1
```

This will automatically test:
- Health checks
- Authentication (dev-login)
- Dashboard data loading
- Tenant isolation (OrgA vs OrgB)
- Demo case/document discovery
- **OCR pipeline (enqueues and waits for completion - ~60-90 seconds)**
- Rules evaluation
- Export generation (discrepancy letter + bank pack)
- Audit logging

**Expected output:** All 12 tests PASS ✅

**Expected runtime:** ~2-5 minutes (including OCR processing time)

**What smoke test verifies:**
- All core services are running and healthy
- Authentication and authorization work
- Tenant isolation is enforced (OrgA cannot see OrgB data)
- Demo artifacts (case + document) are created and accessible
- OCR pipeline processes documents successfully
- Rules engine evaluates cases and creates exceptions
- Exports generate correctly with valid presigned URLs
- Audit logging captures all actions

### Step 3: Access the Platform
1. Open browser: http://localhost:3000/dashboard
2. Login as: `admin@orga.com` (any password works in dev mode)
3. Select Org: "OrgA", Role: "Admin"
4. Navigate through:
   - Dashboard → View case metrics
   - Cases → Open a case → View documents
   - Documents → View OCR text, attach evidence
   - Rules → Evaluate rules, view exceptions
   - Exports → Generate bank pack PDF

**Demo Credentials:**
- OrgA Admin: `admin@orga.com`
- OrgA Reviewer: `reviewer@orga.com`
- OrgB Admin: `admin@orgb.com`

**Access URLs:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin / change_me)
- MailHog: http://localhost:8025

---

## Real Document Testing

For testing with real bank diligence documents, see:
- **[Real Document Playbook](09_pilot_real_docs_playbook.md)** - Complete guide for uploading and processing real documents
- **Quick upload script:** `.\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\your_doc.pdf"`

## Quick Start (Fresh Install)

1. **Clean start (removes all volumes):**
   ```bash
   docker compose down -v
   ```

2. **Build and start all services:**
   ```bash
   docker compose up -d --build
   ```

3. **Run database migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

4. **Seed demo data:**
   ```bash
   docker compose exec api python scripts/dev/seed_demo_data.py
   ```

5. **Verify services are running:**
   ```bash
   docker compose ps
   ```
   All services (api, worker, beat, frontend, db, redis, minio, mailhog) should show "Up" status.

6. **Check health:**
   ```bash
   curl.exe http://localhost:8000/api/v1/health/deep
   ```

3. **Access the platform:**
   - Frontend: http://localhost:3000
   - MailHog (email testing): http://localhost:8025
   - API docs: http://localhost:8000/docs

## Demo Script

### Step 1: Login
- Go to http://localhost:3000
- Login as `admin@orga.com` (any role works, Admin recommended)
- Select Org: "OrgA", Role: "Admin"

### Step 2: Dashboard Overview
- View case metrics and trends
- Check recent activity
- Navigate to a case

### Step 3: Case Detail - Documents
- Open a case (e.g., "Property Deal #001")
- Go to Documents tab
- Upload a PDF or view existing documents
- Click "Run OCR" to process pages
- View OCR status: queued/processing/done counts

### Step 4: Document Viewer
- Click on a document to open viewer
- Left panel: document list
- Middle: page thumbnails
- Main: page image with zoom controls
- Bottom: OCR text panel with copy button
- Use "Attach as Evidence" to link page to exception/CP

### Step 5: Dossier Extraction
- Go to Dossier tab
- Click "Extract Fields"
- Review extracted fields grouped by category
- Confirm fields or set source evidence (document+page)
- Toggle "needs_confirmation" for review

### Step 6: Rules Evaluation
- Go to Exceptions tab
- Click "Evaluate Case"
- View generated exceptions and CPs
- Attach evidence to exceptions/CPs from document viewer
- Resolve or waive exceptions (role-based)

### Step 7: Verification Flow
- Go to Verification tab
- Add verification keys (e-stamp, registry ROD)
- Attach evidence from documents
- Mark as Verified or Failed

### Step 8: Exports
- Go to Exports tab (or Reports page)
- Generate Bank Pack PDF
- Generate Discrepancy Letter DOCX
- Download generated exports

### Step 9: Approvals Workflow
- Go to Approvals page
- Create approval request (Reviewer/Admin)
- Approve/Reject as Approver/Admin
- View approval history

### Step 10: Integrations (Admin)
- Go to Integrations page
- Webhooks tab:
  - Create webhook endpoint
  - Copy secret (shown once)
  - View deliveries
  - Test webhook
- Email tab:
  - View email templates
  - Send test email
  - Check MailHog at http://localhost:8025

### Step 11: Admin & Reports
- Admin page: Manage users, view audit logs
- Reports page: Generate case reports
- Analytics page: View trends and metrics

### Step 12: Tenant Isolation Verification
- Logout and login as `admin@orgb.com`
- Verify OrgB sees only OrgB cases/users/audit logs
- OrgB cannot access OrgA data (404/empty)

## Key Features Demonstrated

✅ **OCR Reliability:**
- Preprocessing (grayscale, contrast, resize)
- Per-page processing with idempotency
- Status tracking (queued/processing/done/failed)
- Force re-run support

✅ **Document Viewer:**
- Multi-document navigation
- Page thumbnails
- Zoom controls
- OCR text display
- Evidence attachment

✅ **Evidence Linking:**
- Attach document+page to exceptions
- Attach document+page to CPs
- Set source evidence for dossier fields

✅ **Admin Features:**
- User management (create, role change)
- Audit log viewing with filters
- Tenant isolation enforced

✅ **Integrations:**
- Webhook endpoints with HMAC signing
- Email templates with variable replacement
- Delivery logs and retry mechanism

## Verification Commands

```bash
# Check health
curl http://localhost:8000/api/v1/health/deep

# Check OCR status
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/documents/<doc_id>/ocr-status

# Check audit logs
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/admin/audit?days=7&limit=20"

# SQL verification
docker compose exec db psql -U bank_diligence -d bank_diligence -c "
  SELECT action FROM audit_log 
  WHERE action LIKE 'ocr.%' OR action LIKE 'exception.evidence%' OR action LIKE 'admin.%'
  ORDER BY created_at DESC LIMIT 10;
"
```

## Troubleshooting

- **OCR not processing:** Check worker logs: `docker compose logs worker`
- **Email not sending:** Verify MailHog is running and check SMTP config
- **Webhook failures:** Check delivery logs in Integrations UI
- **Tenant isolation issues:** Verify all queries filter by org_id

