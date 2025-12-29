# Bank Diligence Platform - PostgreSQL Restore Script (PowerShell)
# Restores database from a pg_dump backup file

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$ContainerName = "bank-diligence-platform-db-1"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Host "Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

# Handle gzipped backups
$RestoreFile = $BackupFile
if ($BackupFile -like "*.gz") {
    Write-Host "Decompressing backup file..." -ForegroundColor Cyan
    $RestoreFile = $BackupFile -replace "\.gz$", ""
    gunzip -k $BackupFile
}

Write-Host "=== WARNING ===" -ForegroundColor Yellow
Write-Host "This will DROP and recreate the database 'bank_diligence'." -ForegroundColor Yellow
Write-Host "All existing data will be lost!" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Type 'RESTORE' to confirm"

if ($confirm -ne "RESTORE") {
    Write-Host "Restore cancelled." -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Starting restore..." -ForegroundColor Cyan
Write-Host "Container: $ContainerName"
Write-Host "Restore file: $RestoreFile"

# Drop and recreate database
Write-Host "Dropping existing database..." -ForegroundColor Cyan
docker exec $ContainerName psql -U bank_diligence -d postgres -c "DROP DATABASE IF EXISTS bank_diligence;"
docker exec $ContainerName psql -U bank_diligence -d postgres -c "CREATE DATABASE bank_diligence;"

# Restore from backup
Write-Host "Restoring from backup..." -ForegroundColor Cyan
Get-Content $RestoreFile | docker exec -i $ContainerName psql -U bank_diligence -d bank_diligence

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Restore failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nIMPORTANT: Run migrations to ensure schema is up-to-date:" -ForegroundColor Cyan
Write-Host "  docker compose exec api alembic upgrade head" -ForegroundColor White

