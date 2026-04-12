# Bank Diligence Platform (CDS)

CDS, the Case Diligence Suite, is a Pakistan-first legal diligence platform for property-backed finance. It ingests property documents, runs OCR and extraction workflows, assembles a structured dossier, surfaces Exceptions and Conditions Precedent (CPs), produces draft outputs, and packages the matter into a Bank Pack export for legal and credit review.

## What The Platform Produces

- Dossier
- Exceptions
- Conditions Precedent (CPs)
- Drafts
- Bank Pack export

## Current Stack

Local Docker Compose runs the full application stack:

- Next.js frontend
- FastAPI backend
- PostgreSQL
- Redis
- MinIO
- Celery worker
- Celery beat
- OCR service
- HF extractor service
- MailHog for local email testing

`docker-compose.prod.yml` adds:

- `migrate` one-shot migration container
- `caddy` reverse proxy for production-style local or pilot deployment

## Prerequisites

Install these before cloning:

- Git
- Docker Desktop, or Docker Engine with the Compose v2 plugin
- At least 8 GB RAM available to Docker
- At least 10 GB free disk for images, Postgres, MinIO, and OCR artifacts

Optional:

- Node.js 20+ only if you want to run frontend lint/typecheck outside containers
- Python 3.12+ only if you want to run backend scripts outside containers

## Quick Start

This is the canonical local dev/bootstrap flow for a fresh clone.

### PowerShell

```powershell
git clone <repo-url>
cd bank-diligence-platform
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec -T api alembic upgrade head
docker compose exec -T api python scripts/dev/seed_demo_data.py
```

### Bash

```bash
git clone <repo-url>
cd bank-diligence-platform
cp .env.example .env
docker compose up -d --build
docker compose exec -T api alembic upgrade head
docker compose exec -T api python scripts/dev/seed_demo_data.py
```

After that:

- Frontend: `http://localhost:3000/dashboard`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health/deep`

Demo credentials after seeding:

- `admin@orga.com / ChangeMe123!`
- `reviewer@orga.com / ChangeMe123!`
- `admin@orgb.com / ChangeMe123!`

Windows convenience helpers:

- `.\start-services.ps1`
- `.\scripts\dev\pilot_reset.ps1`

`pilot_reset.ps1` is a heavier reset-and-seed helper. The explicit commands above are the canonical clone-to-run path.

## Environment Setup

### Local Development

Copy `.env.example` to `.env`.

```powershell
Copy-Item .env.example .env
```

The checked-in local defaults are enough to boot the Docker stack on another machine. For normal local use you do not need to change anything before first startup.

Important local variables:

- `APP_ENV=development`
- `POSTGRES_*` defaults match the Compose `db` service
- `MINIO_*` defaults match the Compose `minio` service
- `REDIS_URL=redis://redis:6379/0`
- `API_INTERNAL_BASE_URL=http://api:8000`
- `OCR_SERVICE_URL=http://ocr_service:8001`
- `HF_EXTRACTOR_URL=http://hf-extractor:8090`
- `EMAIL_ENABLED=false` and MailHog defaults keep local email non-delivery-safe

You do not need to set `NEXT_PUBLIC_API_URL` or `NEXT_PUBLIC_API_BASE_URL` for local Docker use. Browser traffic goes through the frontend proxy routes and the server uses `API_INTERNAL_BASE_URL`.

### Production-Style Local / Pilot Deployment

Copy `.env.production.example` to `.env.production`, then replace every placeholder secret and hostname before starting `docker-compose.prod.yml`.

```powershell
Copy-Item .env.production.example .env.production
```

Required before first prod-style start:

- `APP_ENV=production`
- `APP_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- `PUBLIC_HOSTNAME`
- `PUBLIC_URL`
- `CORS_ORIGINS`

Legacy note:

- `.env.prod.example` is deprecated. Use `.env.production.example`.

## Database Migrations

Local dev compose does not auto-run Alembic. Run this after `docker compose up -d --build`:

```powershell
docker compose exec -T api alembic upgrade head
```

`docker-compose.prod.yml` includes a `migrate` service and runs migrations before the API starts. To re-run manually:

```powershell
docker compose -f docker-compose.prod.yml run --rm migrate
```

## Default Local URLs

- Frontend dashboard: `http://localhost:3000/dashboard`
- Backend API docs: `http://localhost:8000/docs`
- Backend deep health: `http://localhost:8000/api/v1/health/deep`
- MinIO console: `http://localhost:9001`
- MailHog: `http://localhost:8025`

The MinIO S3 API is also exposed locally at `http://localhost:9000`.

## Demo / Seed Data

The repository does not ship with a pre-populated database. A fresh machine needs the seed step if you want demo users, demo cases, and OCR/demo documents.

Seed command:

```powershell
docker compose exec -T api python scripts/dev/seed_demo_data.py
```

What the seed creates:

- OrgA and OrgB
- Demo users with fixed passwords
- Multiple cases including `PILOT DEMO CASE`
- Demo documents and OCR page text
- Demo OCR extraction candidate(s)

Reset-and-seed convenience flow on Windows:

```powershell
.\scripts\dev\pilot_reset.ps1
```

That script:

- destroys containers and volumes unless `-KeepVolumes` is used
- rebuilds the stack
- runs migrations
- seeds demo data

## Fresh-Machine Bootstrap Notes

From a clean clone, the only required files you must create before startup are:

- `.env` for local dev, copied from `.env.example`
- `.env.production` only if you intend to use `docker-compose.prod.yml`

Required local startup steps:

1. Copy `.env.example` to `.env`
2. `docker compose up -d --build`
3. `docker compose exec -T api alembic upgrade head`
4. optional but recommended for a usable demo: `docker compose exec -T api python scripts/dev/seed_demo_data.py`

There are no additional hidden manual setup steps after those commands.

## Production-Style Local Startup

Use this only when you want the reverse proxy and production-style env separation locally or in a pilot environment.

```powershell
Copy-Item .env.production.example .env.production
.\scripts\ops\preflight_prod.ps1
docker compose -f docker-compose.prod.yml up -d --build
```

Notes:

- `caddy` publishes `80` and `443`
- `migrate` runs before `api`
- you must replace placeholder secrets first
- `PUBLIC_HOSTNAME` and `PUBLIC_URL` must match your host/domain plan

For the full production runbook, see [docs/ops/DEPLOYMENT_PROD.md](docs/ops/DEPLOYMENT_PROD.md).

## Common Troubleshooting

### OCR Service Uses Too Much CPU

- Lower `OCR_SERVICE_CPUS` in `.env`
- Keep `OCR_MAX_WORKERS=1`
- Keep `CELERY_WORKER_CONCURRENCY=1`
- Recreate the OCR and worker services:

```powershell
docker compose up -d --build ocr_service worker beat
```

### Missing Migrations / Blank Data / Backend 500s After Update

Run:

```powershell
docker compose exec -T api alembic upgrade head
```

If the database was created from a mismatched older checkout, reset local volumes:

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec -T api alembic upgrade head
```

### Worker Or Beat Unhealthy

Inspect container status and logs:

```powershell
docker compose ps
docker compose logs --tail=200 worker beat
```

If Redis or Postgres came up late, recreate the background services:

```powershell
docker compose up -d --build worker beat
```

### Demo Case Is Missing

Run the seed again:

```powershell
docker compose exec -T api python scripts/dev/seed_demo_data.py
```

### OCR Panel Is Blank Or OCR Extractions Look Empty After An Update

First make sure migrations are current:

```powershell
docker compose exec -T api alembic upgrade head
```

Then rebuild the frontend if the running image is stale:

```powershell
docker compose up -d --build frontend
```

### Frontend Route Crash After Pulling New Changes

Rebuild the frontend container:

```powershell
docker compose up -d --build frontend
```

If the backend schema also changed, rerun migrations before reloading the app.

## Verification Checklist

After startup, these checks are enough to confirm the stack is usable:

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8000/api/v1/health/deep -UseBasicParsing
Invoke-WebRequest http://localhost:3000/login -UseBasicParsing
docker compose exec -T api alembic current
```

Optional login smoke check:

```powershell
$body = @{ email = "admin@orga.com"; password = "ChangeMe123!" } | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/api/v1/auth/login -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
```

## Production Note

For development and pilot-style local work, Docker Compose is the recommended path. Public deployment should use `docker-compose.prod.yml`, `.env.production`, and the reverse-proxy configuration in this repo rather than the dev compose stack.
