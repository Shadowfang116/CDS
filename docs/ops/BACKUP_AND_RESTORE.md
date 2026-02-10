# Backup and Restore Runbook (Ops)

This runbook covers **PostgreSQL** and **MinIO** backup/restore for the Bank Diligence Platform in production. Use the scripts under `scripts/ops/` (Windows PowerShell) or run the equivalent commands manually.

---

## 1. PostgreSQL backup (pg_dump custom format)

**Recommended:** Use custom format (`-Fc`) for single-file backup and flexible restore (e.g. parallel, schema-only).

### Using script (Windows)

```powershell
cd <repo-root>
.\scripts\ops\backup_postgres.ps1

# Optional: custom backup directory and container name
.\scripts\ops\backup_postgres.ps1 -BackupDir "D:\backups\postgres" -ContainerName "your-db-container"
```

This creates a **timestamped** file, e.g. `backups\postgres\bank_diligence_20240211_020000.dump`.

### Manual

```powershell
docker exec <db-container> pg_dump -U bank_diligence -d bank_diligence -Fc -f /tmp/backup.dump
docker cp <db-container>:/tmp/backup.dump .\backups\postgres\bank_diligence_<timestamp>.dump
```

Or from host with pipe (custom format must go to file inside container or use `-f -` and redirect):

```powershell
docker exec <db-container> pg_dump -U bank_diligence -d bank_diligence -Fc -f /tmp/backup.dump
docker cp <db-container>:/tmp/backup.dump .\bank_diligence.dump
```

---

## 2. PostgreSQL restore (pg_restore)

**Prerequisites:** Stop API and worker so no connections write to the DB. Optionally stop beat. Keep `db` (and optionally `minio`) running.

### Using script (Windows)

```powershell
.\scripts\ops\restore_postgres.ps1 -BackupFile ".\backups\postgres\bank_diligence_20240211_020000.dump"
```

The script will prompt for confirmation, then drop/recreate the database and run `pg_restore`.

### Manual

```powershell
# 1. Stop app services
docker compose -f docker-compose.prod.yml stop api worker beat

# 2. Drop and recreate database
docker exec <db-container> psql -U bank_diligence -d postgres -c "DROP DATABASE IF EXISTS bank_diligence;"
docker exec <db-container> psql -U bank_diligence -d postgres -c "CREATE DATABASE bank_diligence;"

# 3. Restore (copy dump into container then pg_restore)
docker cp .\bank_diligence.dump <db-container>:/tmp/backup.dump
docker exec <db-container> pg_restore -U bank_diligence -d bank_diligence --no-owner --no-acl /tmp/backup.dump

# 4. Run migrations (in case backup was from older revision)
docker compose -f docker-compose.prod.yml run --rm migrate

# 5. Start services
docker compose -f docker-compose.prod.yml up -d
```

---

## 3. MinIO backup

**Options:**

- **A) mc mirror** (recommended): Use MinIO Client to mirror the bucket to a local directory.
- **B) Volume copy:** Copy the `minio_data` volume directory (e.g. zip the volume mount path).

### Using script (Windows, mc mirror)

```powershell
.\scripts\ops\backup_minio.ps1

# Optional: backup dir, mc alias, bucket name
.\scripts\ops\backup_minio.ps1 -BackupDir "D:\backups\minio" -MinioAlias "local" -Bucket "case-files"
```

Ensure `mc` is installed and alias is set, e.g.:

```powershell
mc alias set local http://localhost:9000 <MINIO_ROOT_USER> <MINIO_ROOT_PASSWORD>
```

### Manual (mc mirror)

```powershell
mc mirror local/case-files .\backups\minio\<timestamp>\case-files --overwrite
```

### Manual (volume zip)

If MinIO data is in a Docker volume or host path, create a timestamped zip of that directory. The script `backup_minio.ps1` can use a volume path if you set it (see script comments).

---

## 4. MinIO restore

### Using script (Windows)

```powershell
.\scripts\ops\restore_minio.ps1 -BackupPath ".\backups\minio\20240211_020000"
```

### Manual

```powershell
mc mirror .\backups\minio\<timestamp>\case-files local/case-files --overwrite
```

---

## 5. Verification after restore

1. **Run migrations**  
   Migrations run automatically on prod startup (migrate service). To run manually:
   ```powershell
   docker compose -f docker-compose.prod.yml run --rm migrate
   ```

2. **Health check**  
   Call the health endpoint, e.g. `GET https://<host>/api/v1/health` or `GET https://<host>/health`. Expect 200.

3. **Migrations status**  
   As Admin, call `GET /api/v1/admin/migrations/status` (with org header). Confirm `current_revision` matches `head_revisions`.

4. **Functional check**  
   Open a case and export a bank pack. Confirm the export completes and the file downloads.

---

## 6. Convenience scripts summary

| Script | Purpose |
|--------|--------|
| `scripts/ops/backup_postgres.ps1` | pg_dump -Fc, timestamped `.dump` file |
| `scripts/ops/restore_postgres.ps1` | Drop DB, create DB, pg_restore from `.dump` |
| `scripts/ops/backup_minio.ps1` | mc mirror bucket to timestamped directory (or volume zip) |
| `scripts/ops/restore_minio.ps1` | mc mirror from backup directory back to bucket |

All scripts are intended for Windows PowerShell and are safe to run from the repo root.

---

## 7. Manual retention run (Phase 9)

Retention runs automatically daily at 2:00 UTC via Celery beat. To trigger it manually (e.g. for verification):

```powershell
docker compose -f docker-compose.prod.yml exec -T worker python -c "from app.workers.tasks_retention import run_retention_now; run_retention_now.delay()"
```

Or dry-run (no deletes):

```powershell
docker compose -f docker-compose.prod.yml exec -T worker python -c "from app.workers.tasks_retention import run_retention_now; run_retention_now.delay(dry_run=True)"
```

---

## 8. Retention and backups

- Retention (Phase 9) deletes **Closed** cases older than `RETENTION_DAYS`; backups may still contain that data until the next backup.
- Keep backups for at least as long as your compliance requires (e.g. ≥ RETENTION_DAYS).
- Encrypt backups at rest where required by policy.
