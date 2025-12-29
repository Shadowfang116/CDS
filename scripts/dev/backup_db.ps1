# Bank Diligence Platform - PostgreSQL Backup Script (PowerShell)
# Creates a timestamped pg_dump backup of the database

param(
    [string]$BackupDir = ".\backups\db",
    [string]$ContainerName = "bank-diligence-platform-db-1"
)

$ErrorActionPreference = "Stop"

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "bank_diligence_$Timestamp.sql"

Write-Host "Starting PostgreSQL backup..." -ForegroundColor Cyan
Write-Host "Container: $ContainerName"
Write-Host "Backup file: $BackupFile"

# Run pg_dump inside the container
docker exec $ContainerName pg_dump -U bank_diligence -d bank_diligence > $BackupFile

if ($LASTEXITCODE -eq 0) {
    $FileSize = (Get-Item $BackupFile).Length / 1KB
    Write-Host "Backup completed successfully!" -ForegroundColor Green
    Write-Host "File size: $([math]::Round($FileSize, 2)) KB"
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}

# Optional: compress the backup
$CompressedFile = "$BackupFile.gz"
Write-Host "Compressing backup..." -ForegroundColor Cyan
& gzip -k $BackupFile 2>$null
if (Test-Path $CompressedFile) {
    $CompressedSize = (Get-Item $CompressedFile).Length / 1KB
    Write-Host "Compressed file: $CompressedFile ($([math]::Round($CompressedSize, 2)) KB)" -ForegroundColor Green
}

Write-Host "`nBackup complete. Files saved to: $BackupDir" -ForegroundColor Cyan

