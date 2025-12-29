# Backup and Restore Guide

## Overview

The Bank Diligence Platform uses two primary data stores:
1. **PostgreSQL** - Structured data (cases, users, audit logs, etc.)
2. **MinIO** - Object storage (PDF documents, exports)

Both must be backed up to ensure complete data recovery.

---

## Prerequisites

### For PostgreSQL Backup
- Docker with running `db` container
- Write access to backup directory

### For MinIO Backup
- [MinIO Client (mc)](https://min.io/download) installed
- mc configured with alias pointing to MinIO instance

Configure mc alias:
```bash
mc alias set local http://localhost:9000 minioadmin <your_password>
```

---

## Database Backup

### Using Scripts

**PowerShell (Windows):**
```powershell
.\scripts\dev\backup_db.ps1

# Custom backup directory:
.\scripts\dev\backup_db.ps1 -BackupDir "D:\backups\db"
```

**Bash (Linux/macOS):**
```bash
chmod +x scripts/dev/backup_db.sh
./scripts/dev/backup_db.sh

# Custom backup directory:
BACKUP_DIR=/backups/db ./scripts/dev/backup_db.sh
```

### Manual Backup

```bash
# Create backup
docker exec bank-diligence-platform-db-1 pg_dump -U bank_diligence -d bank_diligence > backup.sql

# Compress (optional)
gzip backup.sql
```

### Backup Contents
- All tables: orgs, users, cases, documents, exports, audit_log, etc.
- Includes foreign key relationships
- Does NOT include MinIO objects

---

## Database Restore

### Using Scripts

**PowerShell (Windows):**
```powershell
.\scripts\dev\restore_db.ps1 -BackupFile ".\backups\db\bank_diligence_20240101_120000.sql"
```

**Bash (Linux/macOS):**
```bash
chmod +x scripts/dev/restore_db.sh
./scripts/dev/restore_db.sh ./backups/db/bank_diligence_20240101_120000.sql
```

### Manual Restore

```bash
# Stop application services (keep db running)
docker compose stop api worker

# Drop and recreate database
docker exec bank-diligence-platform-db-1 psql -U bank_diligence -d postgres \
  -c "DROP DATABASE IF EXISTS bank_diligence;"
docker exec bank-diligence-platform-db-1 psql -U bank_diligence -d postgres \
  -c "CREATE DATABASE bank_diligence;"

# Restore from backup
cat backup.sql | docker exec -i bank-diligence-platform-db-1 \
  psql -U bank_diligence -d bank_diligence

# Run migrations (if needed)
docker compose exec api alembic upgrade head

# Restart services
docker compose up -d
```

---

## MinIO Backup

### Using Scripts

**PowerShell (Windows):**
```powershell
.\scripts\dev\backup_minio.ps1
```

**Bash (Linux/macOS):**
```bash
chmod +x scripts/dev/backup_minio.sh
./scripts/dev/backup_minio.sh
```

### Manual Backup

```bash
# Mirror entire bucket to local directory
mc mirror local/case-files ./backups/minio/case-files --overwrite
```

### Backup Contents
- All PDF documents (originals and per-page splits)
- All generated exports (DOCX, PDF)
- Organized by: `org/{org_id}/cases/{case_id}/...`

---

## MinIO Restore

### Using Scripts

**PowerShell (Windows):**
```powershell
.\scripts\dev\restore_minio.ps1 -BackupPath ".\backups\minio\20240101_120000"
```

**Bash (Linux/macOS):**
```bash
chmod +x scripts/dev/restore_minio.sh
./scripts/dev/restore_minio.sh ./backups/minio/20240101_120000
```

### Manual Restore

```bash
# Mirror from backup to MinIO
mc mirror ./backups/minio/case-files local/case-files --overwrite
```

---

## Complete Restore Procedure

1. **Stop all services except db and minio:**
   ```bash
   docker compose stop api worker frontend
   ```

2. **Restore PostgreSQL:**
   ```bash
   ./scripts/dev/restore_db.sh ./backups/db/latest.sql
   ```

3. **Restore MinIO:**
   ```bash
   ./scripts/dev/restore_minio.sh ./backups/minio/latest
   ```

4. **Run migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. **Restart all services:**
   ```bash
   docker compose up -d
   ```

6. **Verify:**
   - Check `/health` endpoint
   - Login and verify case data
   - Verify document downloads work

---

## Backup Schedule Recommendations

| Environment | PostgreSQL | MinIO |
|-------------|------------|-------|
| Development | Daily | Weekly |
| Staging | Daily | Daily |
| Production | Every 6 hours | Daily + transaction log shipping |

---

## Disaster Recovery Notes

1. **Point-in-Time Recovery**: For production, enable PostgreSQL WAL archiving for PITR capability.

2. **Cross-Region**: Consider replicating MinIO to a secondary region/bucket.

3. **Testing**: Regularly test restore procedures in a staging environment.

4. **Retention**: Keep backups for at least RETENTION_DAYS (default: 365 days).

5. **Encryption**: Consider encrypting backups at rest for compliance.

