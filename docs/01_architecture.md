# Architecture (MVP)

## Services
- frontend: Next.js
- api: FastAPI
- worker: Celery
- db: Postgres
- redis: queue + cache
- minio: object storage

## Data flow
Upload → store → split pages → OCR → classify → extract → dossier confirm → rules evaluate → exceptions/CP → drafts → bank pack export → audit log

