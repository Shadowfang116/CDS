#!/bin/bash
# Bank Diligence Platform - PostgreSQL Restore Script (Bash)
# Restores database from a pg_dump backup file

set -e

BACKUP_FILE="$1"
CONTAINER_NAME="${CONTAINER_NAME:-bank-diligence-platform-db-1}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql[.gz]>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Handle gzipped backups
RESTORE_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "Decompressing backup file..."
    RESTORE_FILE="${BACKUP_FILE%.gz}"
    gunzip -k "$BACKUP_FILE"
fi

echo "=== WARNING ==="
echo "This will DROP and recreate the database 'bank_diligence'."
echo "All existing data will be lost!"
echo ""
read -p "Type 'RESTORE' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."
echo "Container: $CONTAINER_NAME"
echo "Restore file: $RESTORE_FILE"

# Drop and recreate database
echo "Dropping existing database..."
docker exec "$CONTAINER_NAME" psql -U bank_diligence -d postgres -c "DROP DATABASE IF EXISTS bank_diligence;"
docker exec "$CONTAINER_NAME" psql -U bank_diligence -d postgres -c "CREATE DATABASE bank_diligence;"

# Restore from backup
echo "Restoring from backup..."
cat "$RESTORE_FILE" | docker exec -i "$CONTAINER_NAME" psql -U bank_diligence -d bank_diligence

if [ $? -eq 0 ]; then
    echo "Restore completed successfully!"
else
    echo "Restore failed!"
    exit 1
fi

echo ""
echo "IMPORTANT: Run migrations to ensure schema is up-to-date:"
echo "  docker compose exec api alembic upgrade head"

