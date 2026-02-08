# Phase 10 Fixes - Pilot Readiness

## Root Causes Identified

### 1. Missing Python Dependencies
**Problem:** Containers (api, worker, beat) were crashing with `ModuleNotFoundError: No module named 'cryptography'` and `ModuleNotFoundError: No module named 'httpx'`.

**Root Cause:** Dockerfile was manually listing dependencies instead of installing from `pyproject.toml`, and was missing `cryptography` and `httpx`.

**Fix:** Updated `backend/Dockerfile` to explicitly install all dependencies including `cryptography` and `httpx`.

### 2. Migration Chain Issue (D10)
**Problem:** D10 migration wasn't being applied, and when attempted, it failed with transaction errors.

**Root Cause:** Migration used `try/except` block which doesn't work well with Alembic transactions. The column addition check needed to use raw SQL.

**Fix:** Updated `backend/alembic/versions/h0i1j2k3l4m5_d10_pilot_readiness.py` to check for column existence using `information_schema` before adding.

### 3. Scripts Directory Not Available
**Problem:** Seed script couldn't be found: `python: can't open file '/app/scripts/dev/seed_demo_data.py'`

**Root Cause:** Scripts directory wasn't mounted as a volume in docker-compose.yml for the api service.

**Fix:** Added volume mount `./scripts:/app/scripts:ro` to api, worker, and beat services in `docker-compose.yml`.

### 4. Seed Script Python Path
**Problem:** Seed script failed with `ModuleNotFoundError: No module named 'app'`.

**Root Cause:** Script was trying to calculate backend path relative to file location, but in container `/app` is the backend root.

**Fix:** Updated `scripts/dev/seed_demo_data.py` to use `/app` directly as Python path.

### 5. Seed Script Missing Required Field
**Problem:** Seed script failed with `null value in column "name" of relation "digest_schedules" violates not-null constraint`.

**Root Cause:** `DigestSchedule` model requires a `name` field, but seed script wasn't providing it.

**Fix:** Added `name="Daily Digest"` to `DigestSchedule` creation in seed script.

### 6. Missing Restart Policies
**Problem:** Containers would exit and not restart automatically.

**Fix:** Added `restart: unless-stopped` to api, worker, beat, and frontend services.

### 7. Missing Model Import
**Problem:** `CPEvidenceRef` model wasn't imported in `app/main.py`, causing potential issues.

**Fix:** Added `CPEvidenceRef` to imports in `backend/app/main.py`.

## Files Modified

1. **backend/Dockerfile**
   - Added explicit installation of `cryptography` and `httpx`
   - Removed attempt to copy scripts (now mounted via volume)

2. **backend/alembic/versions/h0i1j2k3l4m5_d10_pilot_readiness.py**
   - Fixed column existence check using `information_schema` instead of try/except

3. **docker-compose.yml**
   - Added `restart: unless-stopped` to api, worker, beat, frontend
   - Added `./scripts:/app/scripts:ro` volume mount to api, worker, beat
   - Updated frontend `depends_on` to use `condition: service_started`

4. **scripts/dev/seed_demo_data.py**
   - Changed Python path from relative calculation to `/app`
   - Added `name="Daily Digest"` to `DigestSchedule` creation

5. **backend/app/main.py**
   - Added `CPEvidenceRef` to model imports

6. **docs/08_demo_walkthrough.md**
   - Updated with golden path commands

## Verification Results

✅ **All containers running:**
```
api, worker, beat, frontend, db, redis, minio, mailhog - all Up
```

✅ **Migrations applied:**
```
D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8 → D9 → D10 (h0i1j2k3l4m5)
```

✅ **Database tables created:**
- `audit_log` exists (verified: `SELECT count(*) FROM audit_log;`)
- `cp_evidence_refs` exists (verified: `\d cp_evidence_refs`)

✅ **Health check passes:**
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok"},
    "redis": {"status": "ok"},
    "minio": {"status": "ok", "bucket": "case-files"},
    "worker": {"status": "ok", "active_workers": 1}
  }
}
```

✅ **Seed data created:**
- 8 cases (5 OrgA + 3 OrgB)
- 6 users (4 OrgA + 2 OrgB)
- 9 documents with pages
- Audit logs: 0 (seed script doesn't create audit logs, but table exists)

✅ **Frontend accessible:**
- http://localhost:3000 loads successfully

## Acceptance Criteria Met

✅ After `docker compose down -v` → `docker compose up -d --build` → `alembic upgrade head` → `seed_demo_data.py`:
- All services (api, worker, beat) are RUNNING
- Health endpoint returns 200 with all checks OK
- Frontend dashboard loads (no network error)
- `audit_log` table exists and queryable
- Alembic head includes D10 and applies successfully

## Next Steps for User

1. **Test the platform:**
   ```bash
   # Open frontend
   start http://localhost:3000
   
   # Login as admin@orga.com
   # Navigate to /dashboard
   ```

2. **Verify tenant isolation:**
   ```bash
   # Login as admin@orgb.com
   # Verify OrgB sees only OrgB data
   ```

3. **Test OCR:**
   ```bash
   # Upload a document in a case
   # Run OCR
   # Check status via API or UI
   ```

4. **Test integrations:**
   ```bash
   # Go to /integrations
   # Create webhook endpoint
   # Send test email (check MailHog at http://localhost:8025)
   ```

## Summary

All critical issues have been resolved:
- ✅ Dependencies installed correctly
- ✅ Migrations chain complete (D1-D10)
- ✅ Scripts accessible via volume mount
- ✅ Seed script runs successfully
- ✅ All containers running with restart policies
- ✅ Health checks passing
- ✅ Frontend connects to API

The platform is now ready for pilot testing.

