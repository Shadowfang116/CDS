#!/usr/bin/env bash
set -euo pipefail
echo "[migrate] Running alembic upgrade head"
cd /app
alembic upgrade head
echo "[migrate] Done"
