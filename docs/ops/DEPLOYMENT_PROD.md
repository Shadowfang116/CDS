# Production Deployment Runbook

Deploy the Bank Diligence Platform for on-prem pilots and bank IT. Copy/paste-friendly.

---

## 1. Prerequisites

- **Docker** and **Docker Compose** (v2+)
- **Disk sizing (guidance):**
  - `db_data` volume: plan for ~2–5 GB per 10k cases + growth (indexes, audit log)
  - `minio_data` volume: plan for document storage (e.g. 50–200 MB per case depending on PDFs)
- **Ports in use:**

| Port | Service   | Notes                    |
|------|-----------|--------------------------|
| 3000 | frontend  | Web UI                   |
| 8000 | api       | REST API                 |
| 9000 | minio     | S3 API                   |
| 9001 | minio     | MinIO Console (optional)  |

Ensure these ports are free or map them via your reverse proxy.

---

## 2. One-command start

```powershell
# From repo root
cp .env.prod.example .env
# Edit .env: replace all REPLACE_ME_* with strong secrets (see ENVIRONMENT_MATRIX.md)

docker compose -f docker-compose.prod.yml up -d --build
```

- The **migrate** service runs first (after `db` is healthy) and runs `alembic upgrade head`.
- The **api** starts only after **migrate** has completed successfully.
- If migration fails, the API does not start.

---

## 3. Health verification

- **API deep health:**  
  `GET https://<host>:8000/api/v1/health/deep`  
  Expect 200 and `status: ok` with postgres, redis, minio checks.

- **Frontend:**  
  Open `https://<host>:3000/dashboard` (or http if no TLS). Login and load a case.

- **Migrations gate:**  
  `docker compose -f docker-compose.prod.yml ps`  
  Confirm **migrate** has exited 0 (not restarting). **api** and **frontend** should be **Up** and healthy.

- **Migrations status (Admin):**  
  `GET /api/v1/admin/migrations/status` with Admin auth and org header.  
  Confirm `current_revision` matches `head_revisions`.

---

## 4. TLS / Reverse proxy (TLS-ready)

TLS is not mandatory for internal pilots; for production-facing deployments use a reverse proxy.

**Minimal Nginx example** (map to your host and cert paths):

```nginx
server {
    listen 443 ssl;
    server_name YOUR_PUBLIC_HOSTNAME;
    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }

    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

**Headers to preserve:** `X-Request-ID`, `X-Forwarded-For`, `X-Forwarded-Proto` (and `Host`).

**Caddy (minimal):**

```caddy
YOUR_PUBLIC_HOSTNAME {
    reverse_proxy / frontend:3000
    reverse_proxy /api/* api:8000
}
```

---

## 5. Access model

- **Roles:** Admin, Reviewer, Approver, Viewer (see product docs).
- **Tenant isolation:** All data is scoped by **org_id**. The **org_id** is never taken from the client; it is derived from the authenticated user session (JWT and server-side role mapping). Client-supplied org is ignored for authorization.

---

## 6. Daily operations

- **Backups:** See [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md) for Postgres (pg_dump custom) and MinIO (mc mirror / volume).
- **Retention:** Runs automatically daily at 2:00 UTC (Celery beat). Manual trigger and dry-run are documented in BACKUP_AND_RESTORE.md.
- **Migrations status:** Use `GET /api/v1/admin/migrations/status` (Admin) to confirm DB revision vs code head after deployments.

---

## 7. Upgrade procedure

1. **Pre-upgrade:** Take backups (Postgres + MinIO). See [BACKUP_AND_RESTORE.md](./BACKUP_AND_RESTORE.md).
2. Pull new version (e.g. `git pull` or pull new image tags).
3. Run:  
   `docker compose -f docker-compose.prod.yml up -d --build`  
   Migrate runs automatically before the API starts.
4. Confirm **migrate** completed, then **api** and **frontend** healthy (see Health verification above).
5. **Rollback:** See [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) for rollback steps (revert tag, restore DB/MinIO if needed).

---

## 8. Preflight and diagnostics

- **Preflight (before start):**  
  `.\scripts\ops\preflight_prod.ps1`  
  Checks Docker, Compose, `.env`, required vars, and warns on placeholders/short secrets.

- **Collect diagnostics (during incidents):**  
  `.\scripts\ops\collect_diagnostics.ps1`  
  Produces a timestamped folder under `./diagnostics/` for support. See [INCIDENT_RUNBOOK.md](./INCIDENT_RUNBOOK.md).
