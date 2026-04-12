#!/usr/bin/env bash
set -euo pipefail

echo "[init_db] Running alembic upgrade head in the api container"
docker compose exec -T api alembic upgrade head
echo "[init_db] Done"
