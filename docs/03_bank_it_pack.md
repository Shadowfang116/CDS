# Bank IT Documentation Pack

**Version**: 1.0  
**Last Updated**: 2024  
**Classification**: Internal - IT Operations

---

## 1. System Architecture Overview

The Bank Diligence Platform is a multi-tenant document analysis and due diligence system deployed as containerized microservices.

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL                                   │
│                                                                         │
│    ┌─────────────┐                                                      │
│    │   Browser   │ ──────────────────────────────────────────────────┐  │
│    │  (End User) │                                                   │  │
│    └─────────────┘                                                   │  │
│                                                                      │  │
└──────────────────────────────────────────────────────────────────────│──┘
                                                                       │
┌──────────────────────────────────────────────────────────────────────│──┐
│                           APPLICATION LAYER                          │  │
│                                                                      │  │
│    ┌──────────────────┐    ┌──────────────────┐                      │  │
│    │    Frontend      │◄───│    API Server    │◄─────────────────────┘  │
│    │   (Next.js)      │    │    (FastAPI)     │                         │
│    │   Port 3000      │────│    Port 8000     │                         │
│    └──────────────────┘    └────────┬─────────┘                         │
│                                     │                                    │
│                            ┌────────┴────────┐                          │
│                            │                 │                          │
│                    ┌───────▼──────┐  ┌───────▼──────┐                   │
│                    │    Worker    │  │    Redis     │                   │
│                    │   (Celery)   │  │  Port 6379   │                   │
│                    └───────┬──────┘  └──────────────┘                   │
│                            │                                            │
└────────────────────────────│────────────────────────────────────────────┘
                             │
┌────────────────────────────│────────────────────────────────────────────┐
│                       DATA LAYER                                        │
│                            │                                            │
│    ┌───────────────────────┴───────────────────────┐                    │
│    │                                               │                    │
│    ▼                                               ▼                    │
│  ┌──────────────────┐                    ┌──────────────────┐           │
│  │   PostgreSQL     │                    │      MinIO       │           │
│  │   Port 5432      │                    │   Port 9000/9001 │           │
│  │  (Structured)    │                    │   (Objects)      │           │
│  └──────────────────┘                    └──────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Services and Ports

| Service | Internal Port | External Port | Protocol | Description |
|---------|---------------|---------------|----------|-------------|
| PostgreSQL | 5432 | 5432 | TCP | Primary database |
| API Server | 8000 | 8000 | HTTP | Backend REST API |
| Frontend | 3000 | 3000 | HTTP | Next.js web UI |
| MinIO API | 9000 | 9000 | HTTP/S3 | Object storage API |
| MinIO Console | 9001 | 9001 | HTTP | MinIO admin UI |
| Redis | 6379 | - | TCP | Message broker (internal only) |
| Celery Worker | - | - | - | Background task processor |

### 2.1 Network Exposure

**Internet-facing (after reverse proxy):**
- Frontend: Port 3000
- API: Port 8000

**Internal only:**
- PostgreSQL: Port 5432
- Redis: Port 6379
- MinIO: Ports 9000, 9001 (or proxied)
- Celery Worker: No network exposure

---

## 3. Data Flow

### 3.1 Document Upload Flow

```
User Browser
     │
     ▼ (1) POST /cases/{id}/documents (multipart/form-data)
┌─────────────────┐
│   API Server    │
└────────┬────────┘
         │ (2) Validate PDF, tenant isolation
         │
         ├──────────────────────────────┐
         │                              │
         ▼ (3) Insert document record   ▼ (4) Store PDF in MinIO
┌─────────────────┐              ┌─────────────────┐
│   PostgreSQL    │              │      MinIO      │
└─────────────────┘              └─────────────────┘
         │                              │
         ▼ (5) Split PDF into pages     │
         │                              │
         └──────────────────────────────┘
                      │
                      ▼ (6) Enqueue OCR task
               ┌─────────────────┐
               │      Redis      │
               └────────┬────────┘
                        │
                        ▼ (7) Process OCR
               ┌─────────────────┐
               │  Celery Worker  │
               └────────┬────────┘
                        │
                        ▼ (8) Store OCR text
               ┌─────────────────┐
               │   PostgreSQL    │
               └─────────────────┘
```

### 3.2 Export Generation Flow

```
User Browser
     │
     ▼ (1) POST /cases/{id}/exports/bank-pack
┌─────────────────┐
│   API Server    │──┐
└────────┬────────┘  │
         │           │
         │ (2) Load case data, exceptions, CPs
         ▼           │
┌─────────────────┐  │
│   PostgreSQL    │  │
└─────────────────┘  │
         │           │
         │           ▼ (3) Generate PDF
         │    ┌─────────────────┐
         │    │   ReportLab     │
         │    └────────┬────────┘
         │             │
         │             ▼ (4) Store export PDF
         │      ┌─────────────────┐
         └─────►│      MinIO      │
                └────────┬────────┘
                         │
                         ▼ (5) Return presigned URL
                ┌─────────────────┐
                │   API Server    │
                └────────┬────────┘
                         │
                         ▼
                   User Browser
```

---

## 4. Data Storage

### 4.1 PostgreSQL Tables

| Table | Description | PII/Sensitive |
|-------|-------------|---------------|
| `orgs` | Organization/tenant records | Yes (org names) |
| `users` | User accounts | Yes (emails) |
| `user_org_roles` | Role assignments | No |
| `cases` | Case records | Yes (case details) |
| `documents` | Document metadata | Yes (filenames) |
| `document_pages` | Per-page OCR data | Yes (OCR text) |
| `case_dossier_fields` | Extracted data | Yes (CNICs, names) |
| `exceptions` | Due diligence findings | Moderate |
| `cps` | Conditions precedent | No |
| `exception_evidence_refs` | Evidence links | No |
| `rule_runs` | Rule evaluation history | No |
| `exports` | Generated document registry | No |
| `audit_log` | Audit trail | Yes (user actions) |

### 4.2 MinIO Bucket Structure

```
case-files/
└── org/
    └── {org_id}/
        └── cases/
            └── {case_id}/
                ├── docs/
                │   └── {document_id}/
                │       ├── original.pdf
                │       └── pages/
                │           ├── 1.pdf
                │           ├── 2.pdf
                │           └── ...
                └── exports/
                    └── {export_id}/
                        └── {filename}.pdf|.docx
```

---

## 5. Authentication & Authorization

### 5.1 Authentication
- JWT tokens with HS256 signing
- Token expiry: 24 hours (configurable)
- Tokens issued via `/auth/dev-login` (dev mode only)

### 5.2 Authorization (RBAC)
| Role | Capabilities |
|------|--------------|
| Admin | Full access, delete operations, retention cleanup |
| Approver | Waive exceptions, all Reviewer capabilities |
| Reviewer | Case management, document upload, resolve exceptions |

### 5.3 Tenant Isolation
- All data rows include `org_id` column
- All queries filter by authenticated user's `org_id`
- Cross-tenant data access is architecturally prevented

---

## 6. Audit Logging

### 6.1 Logged Events

| Event Category | Example Actions |
|----------------|-----------------|
| Authentication | `auth.dev_login` |
| Cases | `case.create`, `case.list`, `case.view`, `case.delete` |
| Documents | `document.upload`, `document.download`, `document.delete` |
| OCR | `ocr.enqueue`, `ocr.document_complete` |
| Rules | `rules.evaluate`, `exception.resolve`, `exception.waive` |
| Exports | `export.generate`, `export.download`, `export.delete` |
| Admin | `retention.run` |

### 6.2 Audit Log Schema
- `id`: UUID
- `org_id`: Tenant identifier
- `actor_user_id`: Who performed action
- `action`: Action type
- `entity_type`: What was affected
- `entity_id`: Specific entity UUID
- `event_metadata`: JSON with request details (IP, user-agent, etc.)
- `created_at`: Timestamp

### 6.3 Log Retention
- Audit logs are retained indefinitely by default
- Production recommendation: Archive to cold storage after 2 years

---

## 7. Data Retention & Deletion

### 7.1 Retention Policy
- Default retention: 365 days (configurable via `RETENTION_DAYS`)
- Retention cleanup is triggered manually via Admin endpoint

### 7.2 Deletion Capabilities

| Endpoint | Who | What's Deleted |
|----------|-----|----------------|
| `DELETE /admin/cases/{id}` | Admin | Case + all related data + MinIO objects |
| `DELETE /admin/documents/{id}` | Admin | Document + pages + MinIO objects |
| `DELETE /admin/exports/{id}` | Admin | Export record + MinIO object |
| `POST /admin/run-retention-cleanup` | Admin | Cases older than RETENTION_DAYS |

### 7.3 Deletion Cascade
When a case is deleted:
1. Exports for the case
2. Exception evidence references
3. Exceptions
4. Conditions precedent
5. Rule runs
6. Dossier fields
7. Document pages
8. Documents
9. Case record
10. All MinIO objects under `org/{org_id}/cases/{case_id}/`

---

## 8. Security Controls

### 8.1 Network Security
- All inter-container communication on Docker network
- Redis not exposed externally
- PostgreSQL exposed only for development (restrict in production)

### 8.2 HTTP Security Headers
| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `X-XSS-Protection` | `1; mode=block` | XSS filter (legacy) |
| `Cache-Control` | `no-store, max-age=0` | Prevent caching |

### 8.3 CORS
- Configured via `CORS_ORIGINS` environment variable
- Default: `http://localhost:3000`
- Production: Set to actual frontend domain only

### 8.4 Upload Limits
- Maximum file size: 50 MB (configurable via `MAX_UPLOAD_SIZE_MB`)
- Allowed content types: `application/pdf` only
- Filename sanitization: Special characters removed, path traversal prevented

---

## 9. Backup & Disaster Recovery

See [07_backup_restore.md](./07_backup_restore.md) for detailed procedures.

### 9.1 Summary
| Component | Backup Method | RTO | RPO |
|-----------|---------------|-----|-----|
| PostgreSQL | pg_dump | 1 hour | 6 hours |
| MinIO | mc mirror | 2 hours | 24 hours |

---

## 10. Monitoring Recommendations

### 10.1 Health Checks
- API: `GET /health` (returns `{"status": "ok"}`)
- PostgreSQL: Docker healthcheck with `pg_isready`
- MinIO: `mc admin info local`

### 10.2 Metrics to Monitor
- API response times
- Celery queue depth
- PostgreSQL connection count
- MinIO storage utilization
- Document upload/OCR failure rates

### 10.3 Log Aggregation
- Container logs: stdout/stderr
- Recommend: Ship to centralized logging (ELK, Splunk, etc.)

---

## 11. Compliance Statement

### 11.1 Data Handling
- All case data is stored within the organization's infrastructure
- No data is transmitted to external services for processing
- OCR is performed locally using Tesseract

### 11.2 AI/ML Training
> **No bank data is used for training AI/ML models.**
> 
> This platform does not transmit any document content, OCR results, or
> case data to external AI services. All processing is performed locally
> within the deployed infrastructure.

### 11.3 Data Sovereignty
- Data resides in PostgreSQL and MinIO within the deployment environment
- No replication to external services
- Export files remain within MinIO until explicitly downloaded

---

## 12. Contact & Support

| Role | Contact |
|------|---------|
| Technical Lead | [Internal Contact] |
| IT Operations | [Internal Contact] |
| Security | [Internal Contact] |
