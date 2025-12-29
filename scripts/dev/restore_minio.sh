#!/bin/bash
# Bank Diligence Platform - MinIO Restore Script (Bash)
# Restores MinIO bucket from local backup directory

set -e

BACKUP_PATH="$1"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
BUCKET="${BUCKET:-case-files}"

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup path not found: $BACKUP_PATH"
    exit 1
fi

echo "=== WARNING ==="
echo "This will overwrite objects in the MinIO bucket '$BUCKET'."
echo "Existing objects with the same keys will be replaced!"
echo ""
read -p "Type 'RESTORE' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting MinIO restore..."
echo "Backup path: $BACKUP_PATH"

# Check if mc is installed
if ! command -v mc &> /dev/null; then
    echo "MinIO Client (mc) not found."
    exit 1
fi

# Determine source path
SOURCE_PATH="$BACKUP_PATH"
if [ -d "$BACKUP_PATH/$BUCKET" ]; then
    SOURCE_PATH="$BACKUP_PATH/$BUCKET"
fi

# Mirror back to MinIO
echo "Restoring to bucket: $BUCKET"
mc mirror "$SOURCE_PATH" "$MINIO_ALIAS/$BUCKET" --overwrite

if [ $? -eq 0 ]; then
    echo "Restore completed successfully!"
else
    echo "Restore failed!"
    exit 1
fi

