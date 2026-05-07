# Deployment

## Prerequisites

- Docker Engine with the Compose plugin
- A Linux host or VM with ports `80` and `443` forwarded to it
- A DNS `A` record for `cases.example.com` pointing to your public IP
- `pg_dump`, `tar`, and `mc` installed on the host if you want to run `scripts/backup.sh`

## Clone And Configure

1. Clone the repository to the host.
2. Copy `.env.production.example` to `.env.production`.
3. Replace every placeholder secret in `.env.production`.
4. Confirm `CORS_ORIGINS`, `PUBLIC_URL`, and `PUBLIC_HOSTNAME` match your public domain.

## Network Setup

1. Create the DNS `A` record for `cases.example.com`.
2. Forward TCP `80` and `443` from your router or firewall to the deployment host.
3. Keep Postgres, Redis, MinIO, and service ports private. Only caddy should be exposed publicly.

## Start The Stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The `migrate` service runs Alembic before the API starts. If you prefer to run migrations manually, use the commands listed below in the release checklist.

## First Admin User

1. Sign in to the API container or expose the API through caddy first.
2. Create the first organization record if your database is empty.
3. Create the first admin user through the authenticated admin or auth user-creation endpoint with a temporary password.

Example request after you already have an admin session cookie:

```bash
curl -X POST https://cases.example.com/api/v1/admin/users \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "email": "admin@example.com",
    "full_name": "Platform Admin",
    "role": "Admin",
    "temporary_password": "ChangeMeNow123!"
  }'
```

## Backups

1. Copy `scripts/backup.sh` to the host if you deploy from an image-only bundle, or run it directly from the repo checkout.
2. Export the same environment variables used by `.env.production`, or set `ENV_FILE=/path/to/.env.production`.
3. Run the script manually first:

```bash
./scripts/backup.sh
```

4. Add a cron job or systemd timer after the manual run succeeds.

## Release Checklist

```bash
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```
