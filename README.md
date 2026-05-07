# Covenant Diligence Systems

Covenant Diligence Systems is an on-prem, bank-ready diligence platform for Pakistan property finance documentation. The platform ingests legal and title documents, runs OCR and extraction workflows, assembles a structured dossier, tracks Exceptions and Conditions Precedent, and exports a reviewable bank pack for legal, credit, and approval teams.

## MVP Scope

- Case intake and document upload
- OCR and document-page review
- Dossier assembly and field autofill
- Exceptions, Waivers, Evidence, and Annexures tracking
- Conditions Precedent workflow and approval routing
- Audit timeline and signed download links
- DOCX and PDF export for bank pack preparation

## Tech Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic, Celery
- Database: PostgreSQL
- Queue / cache: Redis
- Object storage: MinIO
- OCR: local OCR service, Tesseract, PaddleOCR, HF extractor
- Packaging: Docker Compose, Caddy for pilot / production-style ingress

## Repo Layout

- `frontend/`: Next.js UI and proxy routes
- `backend/`: FastAPI app, models, services, workers, migrations
- `ocr_service/`: local OCR microservice
- `docs/`: operational docs, security notes, walkthroughs, runbooks
- `scripts/`: dev, backup, and ops helpers
- `templates/`: export templates and document assets

## Environment Setup

Copy the root example file before running Docker Compose:

```powershell
Copy-Item .env.example .env
```

Service-specific reference files are also included:

- `backend/.env.example`
- `frontend/.env.example`
- `.env.production.example`

Required secret-bearing values must stay local:

- `POSTGRES_PASSWORD`
- `APP_SECRET_KEY`
- `MINIO_ROOT_PASSWORD`
- `SMTP_PASSWORD` when email is enabled
- `INTEGRATIONS_ENCRYPTION_KEY` when external integrations are enabled

## Local Docker Compose Setup

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec -T api alembic upgrade head
```

Useful local endpoints:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- Deep health: `http://localhost:8000/api/v1/health/deep`
- MinIO console: `http://localhost:9001`
- MailHog: `http://localhost:8025`

To seed pilot-safe demo data:

```powershell
docker compose exec -T api python scripts/dev/seed_demo_data.py
```

## Running Services Without Compose

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend expects `API_INTERNAL_BASE_URL` for server-side proxying. For direct browser-side debugging you may also set `API_BASE_URL`.

## Database Migrations

Apply migrations in Docker:

```powershell
docker compose exec -T api alembic upgrade head
```

Production-style compose includes a dedicated migration container:

```powershell
docker compose -f docker-compose.prod.yml run --rm migrate
```

## Tests And Quality Checks

Backend:

```powershell
cd backend
python -m compileall app
python -m pytest
```

Frontend:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

Compose validation:

```powershell
docker compose config
docker compose -f docker-compose.prod.yml config
```

## Security Notes

- Do not commit `.env`, `.env.local`, `.env.production`, or any real credentials.
- Do not commit real bank documents, CNICs, title records, customer files, generated bank packs, OCR output, or support logs.
- RBAC, audit logging, signed download links, and retention controls are part of the baseline design.
- Backups, restore validation, and pilot release checks are documented under [docs/ops](docs/ops).
- `docs/pilot_samples_real/` is intentionally gitignored for confidential UAT material.

## Case Lifecycle

`New -> Processing -> Review -> Pending Docs -> Ready for Approval -> Approved / Rejected -> Closed`

Bank-facing review language used across the platform:

- Exceptions
- Conditions Precedent
- Waiver
- Evidence
- Annexures
- Approver

## Pilot / On-Prem Deployment

This repository is designed for pilot and on-prem deployment with Docker Compose.

```powershell
Copy-Item .env.production.example .env.production
.\scripts\ops\preflight_prod.ps1
docker compose -f docker-compose.prod.yml up -d --build
```

Use `docker-compose.prod.yml` for production-style runs with:

- Caddy ingress
- migration gating
- internal-only service networking
- persistent Postgres, Redis, and MinIO volumes

See [docs/ops/DEPLOYMENT_PROD.md](docs/ops/DEPLOYMENT_PROD.md) and [docs/ops/RELEASE_CHECKLIST.md](docs/ops/RELEASE_CHECKLIST.md) for the operational runbook.
