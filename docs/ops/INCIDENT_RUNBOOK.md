# Incident Response Runbook

Quick triage, common incidents, diagnostics collection, and restore. For Bank Diligence Platform production.

---

## 1. Quick triage checklist

Run in order; note any failures.

1. **Service status**  
   ```powershell
   docker compose -f docker-compose.prod.yml ps
   ```  
   Check: db, redis, minio **healthy**; migrate **exited 0**; api and frontend **Up**.

2. **API logs (last lines, with request_id)**  
   ```powershell
   docker compose -f docker-compose.prod.yml logs api --tail=100
   ```  
   Search for `request_id` if the user reported one.

3. **Deep health**  
   ```powershell
   curl -s http://localhost:8000/api/v1/health/deep
   ```  
   Expect 200 and `status: ok`; note any failing check (postgres, redis, minio).

4. **Migrations status (Admin)**  
   Call `GET /api/v1/admin/migrations/status` with Admin Bearer token and X-Org-Id header. Confirm `current_revision` matches `head_revisions` (no stuck migration).

---

## 2. Common incidents and actions

### API won't start

- **Cause:** Config fail-fast in production (e.g. placeholder or short secrets).
- **Action:** Check logs: `docker compose -f docker-compose.prod.yml logs api`. Fix `.env`: set `APP_ENV=production` and replace all REPLACE_ME / weak values. See [ENVIRONMENT_MATRIX.md](./ENVIRONMENT_MATRIX.md). Restart: `docker compose -f docker-compose.prod.yml up -d api`.

### Migration failure

- **Symptom:** migrate service exits non-zero; api never starts.
- **Action:** Inspect migrate logs: `docker compose -f docker-compose.prod.yml logs migrate`. Fix schema/conflict or rollback: restore DB from backup (see [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md)), then re-run deploy. Prefer forward-only migrations; rollback = restore snapshot + re-apply from that point if needed.

### Exports stuck or failed

- **Symptom:** Export stays "pending" or shows "failed" with error_code.
- **Action:** Check export status and error_code / error_message in DB or via API. Common: **LO_TIMEOUT** (LibreOffice convert timeout) — increase DOC_CONVERT_TIMEOUT_SECONDS or fix document. Check worker logs if Celery worker is used: `docker compose -f docker-compose.prod.yml logs worker --tail=200`. Use request_id from the export to correlate with API logs.

### MinIO connectivity

- **Symptom:** Health deep check fails on minio; uploads/downloads fail.
- **Action:** Verify bucket exists and credentials: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET. Check MinIO health: `curl -s http://localhost:9000/minio/health/live`. Restart minio and api if needed.

### DB space / performance

- **Symptom:** Slow queries or "disk full" errors.
- **Action:** Check disk usage on the host and on the db_data volume. Run VACUUM ANALYZE (or VACUUM FULL during maintenance window) inside the db container. Consider archiving old audit log or retention run (retention only deletes **Closed** cases older than RETENTION_DAYS).

---

## 3. Collect diagnostics

Run the script to capture a support bundle:

```powershell
.\scripts\ops\collect_diagnostics.ps1
```

This creates `.\diagnostics\<timestamp>\` with compose status, api/migrate/worker logs, health/deep output, and (if token available) migrations/status. Attach this folder to the support ticket. See script for details.

---

## 4. Restore from backup

Follow [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md):

1. Stop api (and worker/beat if present).
2. Restore Postgres: `.\scripts\ops\restore_postgres.ps1 -BackupFile <path>`.
3. Restore MinIO if needed: `.\scripts\ops\restore_minio.ps1 -BackupPath <path>`.
4. Run migrations if required: `docker compose -f docker-compose.prod.yml run --rm migrate`.
5. Start services and verify health and a sample export.

---

## 5. Escalation data to capture for dev team

When opening a ticket, include:

- **request_id** (from API logs or export)
- **export_id** / **case_id** (if export or case-related)
- **Timestamp window** (UTC) of the incident
- **Compose file version** and **image SHAs** (e.g. `docker compose -f docker-compose.prod.yml images`)
- Output of **collect_diagnostics.ps1** (attach the diagnostics folder)
- **Build info** (if available): GET /api/v1/admin/build-info response
