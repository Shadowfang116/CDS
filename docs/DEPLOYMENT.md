# Deployment Operations (Home-Hosted Public Pilot)

## Prerequisites

- Docker Engine and Docker Compose plugin installed
- A domain DNS `A` record pointing to this machine's public IP
- Router/firewall forwarding TCP `443` (and TCP `80` for TLS bootstrap)
- Keep all non-proxy service ports blocked externally

## Initial Deployment

```bash
git clone <repo-url>
cd bank-diligence-platform
cp .env.production.example .env.production
```

Fill every value in `.env.production` before first start (especially `APP_SECRET_KEY`, DB credentials, and MinIO credentials).

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Database Migration

`docker-compose.prod.yml` includes a `migrate` service that runs `alembic upgrade head` before the API starts. For manual re-runs:

```bash
docker compose -f docker-compose.prod.yml run --rm migrate
```

## Rebuild / Update

```bash
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## Demo Mode Toggle

1. Set `DEMO_MODE=true` in `.env.production` if you intentionally want demo-mode behavior.
2. Restart affected services:

```bash
docker compose -f docker-compose.prod.yml up -d api worker beat
```

## Health Checks

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs api
curl https://your-domain.com/api/v1/health/deep
```

## Backups

```bash
bash scripts/backup.sh
```

## Network Safety Notes

- Expose only proxy ports publicly: `443` (and `80` for certificate bootstrap/renewal).
- Do not publish Postgres, Redis, MinIO, worker, beat, or backend ports to the internet.
