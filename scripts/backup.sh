#!/usr/bin/env bash

# Restore: gunzip -c /path/to/backup_YYYY-MM-DD_HH-MM.sql.gz | docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
# Mirror minio data with: docker compose exec minio mc mirror /data /backup-path

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_ROOT}/docker-compose.prod.yml}"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M)"
BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

required_vars=(
  POSTGRES_USER
  POSTGRES_DB
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
done

mkdir -p "${BACKUP_DIR}"

cleanup_on_error() {
  echo "Postgres backup failed at ${TIMESTAMP}" >&2
}

trap cleanup_on_error ERR

compose_env_args=()
if [[ -f "${ENV_FILE}" ]]; then
  compose_env_args=(--env-file "${ENV_FILE}")
fi

echo "Starting Postgres backup ${TIMESTAMP}"
cd "${PROJECT_ROOT}"
docker compose -f "${COMPOSE_FILE}" "${compose_env_args[@]}" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' \
  | gzip > "${BACKUP_PATH}"

echo "Backup completed successfully"
echo "Backup file: ${BACKUP_PATH}"
