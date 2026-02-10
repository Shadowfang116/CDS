#!/usr/bin/env bash
# CI smoke: ensure API starts and /api/v1/health/deep returns 200.
# Usage: run from repo root. Expects docker compose available.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "[ci] Bringing up api, db, redis, minio..."
docker compose up -d api db redis minio

cleanup() {
  echo "[ci] Tearing down..."
  docker compose logs api 2>/dev/null || true
  docker compose down -v
}
trap cleanup EXIT

url="http://localhost:8000/api/v1/health/deep"
deadline=$((SECONDS + 60))
echo "[ci] Waiting for $url (up to 60s)..."

while [ $SECONDS -lt $deadline ]; do
  if code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$url" 2>/dev/null); then
    if [ "$code" = "200" ]; then
      echo "[ci] Health OK (HTTP $code)"
      exit 0
    fi
  fi
  sleep 2
done

echo "[ci] Health check failed: $url did not return 200 within 60s"
echo "[ci] API logs:"
docker compose logs api
exit 1
