#!/bin/bash
# Bank Diligence Platform - MinIO Backup Script (Bash)
# Uses mc (MinIO Client) to mirror bucket contents to local directory

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups/minio}"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
BUCKET="${BUCKET:-case-files}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

echo "Starting MinIO backup..."
echo "Backup directory: $BACKUP_PATH"

# Check if mc is installed
if ! command -v mc &> /dev/null; then
    echo "MinIO Client (mc) not found."
    echo "Install it from: https://min.io/download"
    echo ""
    echo "After installing mc, configure it with:"
    echo "  mc alias set $MINIO_ALIAS http://localhost:9000 minioadmin change_me"
    exit 1
fi

# Check if alias is configured
if ! mc alias list "$MINIO_ALIAS" &> /dev/null; then
    echo "MinIO alias '$MINIO_ALIAS' not configured."
    echo "Configure it with:"
    echo "  mc alias set $MINIO_ALIAS http://localhost:9000 minioadmin change_me"
    exit 1
fi

# Mirror the bucket
echo "Mirroring bucket: $BUCKET"
mc mirror "$MINIO_ALIAS/$BUCKET" "$BACKUP_PATH/$BUCKET" --overwrite

if [ $? -eq 0 ]; then
    echo "Backup completed successfully!"
    
    # Count files
    FILE_COUNT=$(find "$BACKUP_PATH" -type f | wc -l)
    echo "Files backed up: $FILE_COUNT"
else
    echo "Backup failed!"
    exit 1
fi

echo ""
echo "Backup complete. Files saved to: $BACKUP_PATH"

