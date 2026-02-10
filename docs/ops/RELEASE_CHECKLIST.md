# Release Checklist and Rollback Procedure

Use this for each production release of the Bank Diligence Platform.

---

## Pre-release

- [ ] **CI green:** Frontend build, Docker build, and smoke tests pass (e.g. GitHub Actions or local equivalent).
- [ ] **Migrations reviewed:** Run `alembic heads` and `alembic current` (or use GET `/api/v1/admin/migrations/status` on a staging DB). Ensure no conflicting heads; plan for any new migrations in this release.
- [ ] **Backup taken** before upgrade: Postgres (pg_dump custom) and MinIO (mc mirror or volume). See [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md).
- [ ] **Validate .env.prod.example:** Any new or changed variables are documented in [ENVIRONMENT_MATRIX.md](./ENVIRONMENT_MATRIX.md) and reflected in `.env.prod.example`.

---

## Release steps

1. **Pull new version** (e.g. `git pull` or pull new image tags).
2. **Start/upgrade stack:**  
   ```powershell
   docker compose -f docker-compose.prod.yml up -d --build
   ```
3. **Confirm migrate completed:**  
   `docker compose -f docker-compose.prod.yml ps` — migrate should show "Exited (0)".
4. **Confirm api and frontend healthy:**  
   - `GET /api/v1/health/deep` returns 200 and `status: ok`.  
   - Open `/dashboard` and log in.
5. **Run verify scripts (if available):**  
   - `.\scripts\dev\verify_logging_and_audit.ps1`  
   - `.\scripts\dev\verify_exports_hardening.ps1`  
   (Adjust paths/hosts if scripts expect different env.)

---

## Rollback

1. **Revert to previous version:**  
   Check out previous git tag or use previous image tags (e.g. pin image digest in compose or use a rollback tag).

2. **If migration was destructive or DB incompatible:**  
   - Stop api (and worker/beat).  
   - Restore Postgres from the backup taken pre-release: see [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md) (restore_postgres.ps1).  
   - Run migrate for the reverted code if needed:  
     `docker compose -f docker-compose.prod.yml run --rm migrate`.  
   - Start services.

3. **Restore MinIO** if object schema or paths changed and backups were taken: use restore_minio.ps1 per BACKUP_AND_RESTORE.md.

4. **Validate:**  
   - Health deep check 200.  
   - Open a case and run a sample export (e.g. bank pack) to confirm end-to-end.

**Note:** Migrations are intended to be forward-only. Rollback = revert code + restore DB snapshot when necessary; avoid downgrade migrations in production unless explicitly designed and tested.
