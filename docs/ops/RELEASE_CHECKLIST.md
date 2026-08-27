# Release Checklist and Rollback Procedure

Use this for each production release of Covenant Diligence Systems.

---

## Pre-release

- [ ] **Host approved:** Deploy only to a private Linux VM or on-prem server owned by the bank or deployment operator. Do not treat public cloud as the default.
- [ ] **DNS and TLS ready:** Public DNS, certificate ownership, and reverse-proxy ownership are confirmed before the release window.
- [ ] **CI green:** Frontend build, Docker build, and smoke tests pass (e.g. GitHub Actions or local equivalent).
- [ ] **Preflight clean:** `.\scripts\ops\preflight_prod.ps1` passes with no missing, placeholder, or short required secrets and with `docker compose -f docker-compose.prod.yml config` rendering successfully.
- [ ] **Migrations reviewed:** Run `alembic heads` and `alembic current` (or use GET `/api/v1/admin/migrations/status` on a staging DB). Ensure no conflicting heads; plan for any new migrations in this release.
- [ ] **Backup taken** before upgrade: Postgres (pg_dump custom) and MinIO (mc mirror or volume), stored off-host or in protected storage. See [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md).
- [ ] **Validate .env.production.example:** Any new or changed variables are documented in [ENVIRONMENT_MATRIX.md](./ENVIRONMENT_MATRIX.md) and reflected in `.env.production.example`.

### Authenticated browser smoke

Run this against a seeded local or staging environment with a test account. Do not use real borrower documents or production credentials.

- [ ] Open `/login`, sign in as the test Admin or Reviewer, and confirm the protected redirect lands on `/dashboard`.
- [ ] Confirm the first-run tour explains the review queue, matter creation, matter list, and evidence workspace. Dismiss it, open Help, and confirm **Restart tour** shows it again.
- [ ] On an empty queue, confirm **Create a matter** focuses the new-matter form. Create a test matter with a title and optional document.
- [ ] Open the matter and confirm documents, evidence, findings, required evidence, next action, and readiness are visible together.
- [ ] Open a required-evidence item and confirm the document/page context is preserved in the URL and viewer.
- [ ] Confirm provisional OCR values identify their source and cannot silently become accepted values without reviewer confirmation.
- [ ] Confirm a Reviewer can prepare/submit but cannot approve their own request; confirm an Approver/Admin checker can decide it and the audit event is visible.
- [ ] Confirm high-risk and incomplete states include a severity/status label, explanation, and next action without relying on color alone.

---

## Release steps

1. **Pull new version** (e.g. `git pull` or pull new image tags).
2. **Take fresh backups** if the previous backup is stale or if this release touches schema or object storage.
3. **Start/upgrade stack:**
   ```powershell
   docker compose -f docker-compose.prod.yml up -d --build
   ```
4. **Confirm migrate completed:**
   `docker compose -f docker-compose.prod.yml ps` — migrate should show "Exited (0)".
5. **Confirm api and frontend healthy:**
   - `GET /api/v1/health/deep` returns 200 and `status: ok`.  
   - Open `/dashboard` and log in.
6. **Run verify scripts (if available):**
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
