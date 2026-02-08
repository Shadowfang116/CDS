# Pilot UAT Checklist - Phase P12

This checklist ensures the platform is ready for pilot UAT and real-world testing.

## Pre-Flight Checks

### 1. Environment Setup
- [ ] Docker Compose is installed and running
- [ ] All services are healthy: `docker compose ps`
- [ ] Health check passes: `curl http://localhost:8000/api/v1/health/deep`

### 2. Database Migrations
- [ ] Migrations are at head: `docker compose exec api alembic current`
- [ ] All tables exist (verify critical: `audit_log`, `cases`, `documents`, `ocr_extraction_candidates`, `dossier_field_history`)
- **Note:** If you see "Can't locate revision identified by 'XXXXX'" error:
  - This means the database is stamped to a revision that doesn't exist in the codebase
  - Auto-recovery: `pilot_reset.ps1` will automatically reset the DB if this occurs (unless `-KeepVolumes` is used)
  - Manual recovery: `docker compose down -v && docker compose up -d --build && docker compose exec api alembic upgrade head`

### 3. Reset and Seed
- [ ] Run reset: `.\scripts\dev\pilot_reset.ps1`
- [ ] Verify seed output shows `DEMO_CASE_ID` and `DEMO_DOC_ID`
- [ ] Check that demo data is visible in dashboard

### 4. Smoke Tests
- [ ] Run smoke tests: `.\scripts\dev\smoke_test.ps1`
- [ ] All tests pass (no failures)
- [ ] Verify tenant isolation (OrgA vs OrgB)

## UAT Run

### 5. Full UAT Suite
- [ ] Run UAT: `.\scripts\dev\pilot_uat.ps1`
- [ ] Review `scripts/dev/uat_last_run.txt` for summary
- [ ] Verify all exports generated (Bank Pack PDF, Discrepancy Letter DOCX)
- [ ] Check audit log count is > 0

### 6. Real-Doc Suite (if PDFs provided)
- [ ] Place PDFs in `docs/pilot_samples_real/`
- [ ] Re-run UAT: `.\scripts\dev\pilot_uat.ps1`
- [ ] Verify all documents uploaded and OCR completed
- [ ] Check OCR quality levels reported
- [ ] Verify quality gates work (Low quality requires force_confirm)

## Verification Items

### 7. Tenant Isolation
- [ ] Login as OrgA Admin: `admin@orga.com`
- [ ] Verify OrgA cases are visible
- [ ] Logout and login as OrgB Admin: `admin@orgb.com`
- [ ] Verify OrgB cannot see OrgA cases (404/403 on OrgA case URLs)
- [ ] Verify OrgB has its own cases

### 8. OCR Quality Gates
- [ ] Upload a document with low OCR quality (minimal text)
- [ ] Verify OCR status shows `quality_level: "Low"` or `"Critical"`
- [ ] Run autofill to create extraction candidates
- [ ] Verify candidates are flagged `is_low_quality: true`
- [ ] Try to confirm extraction without `force_confirm` → should fail (400)
- [ ] Confirm with `force_confirm: true` → should succeed
- [ ] Verify audit event `ocr.extraction_force_confirm` is logged

### 9. Evidence-First Verification
- [ ] Open a case with ROD verification
- [ ] Try to mark verified without evidence → should fail (400)
- [ ] Attach evidence (document + page or OCR snippet)
- [ ] Mark verified → should succeed
- [ ] Verify audit event is logged

### 10. Controls Checklist
- [ ] Open a case (LDA, DHA, or REVENUE)
- [ ] Navigate to case detail page
- [ ] Verify "Controls & Evidence Checklist" card is visible
- [ ] Check regime is inferred correctly
- [ ] Verify evidence checklist shows "Missing" vs "Provided"
- [ ] Check readiness status (Ready/Blocked) with clear blockers
- [ ] Upload missing evidence document
- [ ] Verify status flips from "Missing" → "Provided"

### 11. Exports Generated and Downloadable
- [ ] Generate Bank Pack PDF export
- [ ] Verify presigned URL is accessible (HEAD/GET returns 200)
- [ ] Download and verify PDF structure
- [ ] Generate Discrepancy Letter DOCX export
- [ ] Verify presigned URL is accessible
- [ ] Download and verify DOCX structure
- [ ] Check exports appear in `uat_last_run.txt`

### 12. Dossier Field Editing and History
- [ ] Open a case dossier
- [ ] Edit a field value (e.g., `property.plot_number`)
- [ ] Verify field is updated
- [ ] Get field history: `GET /api/v1/cases/{id}/dossier/fields/{key}/history`
- [ ] Verify history entry shows:
  - `old_value` and `new_value`
  - `edited_by_user_id`
  - `source_type: "manual"`
  - `edited_at` timestamp
- [ ] Verify audit event `dossier.field_edit` is logged

### 13. OCR Extractions Workflow
- [ ] Run autofill on a case with OCR'd documents
- [ ] Navigate to OCR Extractions tab
- [ ] Verify pending extractions are listed
- [ ] Edit an extraction candidate (change proposed value)
- [ ] Confirm extraction → verify value written to dossier
- [ ] Reject an extraction → verify reason is required
- [ ] Check confirmed/rejected tabs show correct status

## Known Limitations

### Current Limitations
1. **Cohort Export:** May not be fully implemented (optional in UAT)
2. **Real-Doc Suite:** Requires manual PDF placement in `docs/pilot_samples_real/`
3. **OCR Quality:** Quality gates are heuristic-based (avg chars/page, failed pages)

### Mitigations
1. Cohort export is optional; Bank Pack and Discrepancy Letter are mandatory
2. UAT script provides clear instructions if real-doc folder is empty
3. Quality gates are conservative (err on side of caution)

## Troubleshooting

### Alembic Missing Revision Error
**Symptom:** `Can't locate revision identified by 'XXXXX'`

**Cause:** Database is stamped to a migration revision that doesn't exist in the codebase (common in dev environments when migrations are deleted or database is from a different branch).

**Auto-Recovery:**
- `pilot_reset.ps1` automatically detects this error and resets the database (unless `-KeepVolumes` is used)
- The script will:
  1. Stop containers and remove volumes
  2. Rebuild and restart services
  3. Wait for services to be healthy
  4. Retry migrations

**Manual Recovery:**
```powershell
docker compose down -v
docker compose up -d --build
docker compose exec api alembic upgrade head
python scripts/dev/seed_demo_data.py
```

**Prevention:** Always commit migration files to the repository. Never delete migration files that have been applied to any database.

### PowerShell Script Encoding Issues
**Symptom:** PowerShell parser errors with non-ASCII characters (e.g., "â€"" instead of "—")

**Cause:** Scripts contain non-ASCII characters (em dashes, Unicode symbols, emojis) that break PowerShell parsing on some systems.

**Solution:**
- All scripts in `scripts/dev/` are now ASCII-only
- Output tokens use ASCII: `[OK]`, `[FAIL]`, `[WARN]` (no emojis or Unicode)
- Regression guard: `smoke_test.ps1` includes Test 0 that fails if any `.ps1` file contains non-ASCII characters

**Verification:**
- Run `.\scripts\dev\smoke_test.ps1` - Test 0 will catch any non-ASCII characters
- If test fails, check the reported file and line number

### UAT Script Fails
- Check `scripts/dev/uat_last_run.txt` for error details
- Verify all services are running: `docker compose ps`
- Check API logs: `docker compose logs api --tail=100`
- Check worker logs: `docker compose logs worker --tail=100`

### OCR Not Completing
- Check worker is running: `docker compose ps worker`
- Check Redis queue: `docker compose exec redis redis-cli LLEN celery`
- Increase timeout in script if needed (default: 180s per doc)

### Exports Not Generating
- Verify case has documents and OCR is complete
- Check export service logs: `docker compose logs api | grep export`
- Verify MinIO is accessible: `docker compose ps minio`

## Success Criteria

✅ **UAT is successful if:**
1. All pre-flight checks pass
2. UAT script completes without errors
3. All exports are generated and downloadable
4. Tenant isolation is verified
5. Quality gates are enforced
6. Evidence-first verification works
7. Audit logs are populated
8. Dossier field history is tracked

## Next Steps After UAT

1. Review `uat_last_run.txt` for KPIs and metrics
2. Test with real bank documents (if available)
3. Run father demo script: `docs/12_father_demo_script.md`
4. Address any issues found during UAT
5. Prepare for pilot presentation

