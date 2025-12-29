#!/bin/bash
# Bank Diligence Platform - PostgreSQL Backup Script (Bash)
# Creates a timestamped pg_dump backup of the database

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups/db}"
CONTAINER_NAME="${CONTAINER_NAME:-bank-diligence-platform-db-1}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/bank_diligence_$TIMESTAMP.sql"

echo "Starting PostgreSQL backup..."
echo "Container: $CONTAINER_NAME"
echo "Backup file: $BACKUP_FILE"

# Run pg_dump inside the container
docker exec "$CONTAINER_NAME" pg_dump -U bank_diligence -d bank_diligence > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed successfully!"
    echo "File size: $FILE_SIZE"
else
    echo "Backup failed!"
    exit 1
fi

# Compress the backup
echo "Compressing backup..."
gzip -k "$BACKUP_FILE"
COMPRESSED_FILE="$BACKUP_FILE.gz"
if [ -f "$COMPRESSED_FILE" ]; then
    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    echo "Compressed file: $COMPRESSED_FILE ($COMPRESSED_SIZE)"
fi

echo ""
echo "Backup complete. Files saved to: $BACKUP_DIR"

