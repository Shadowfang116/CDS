# Ops: PostgreSQL restore from pg_dump custom format (.dump).
# Run from repo root. Stops no services; ensure API/worker are stopped before restore.

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$ContainerName = "bank-diligence-platform-db-1",
    [string]$DbUser = "bank_diligence",
    [string]$DbName = "bank_diligence"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Host "Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

Write-Host "=== WARNING ===" -ForegroundColor Yellow
Write-Host "This will DROP and recreate the database '$DbName'. All existing data will be lost!" -ForegroundColor Yellow
$confirm = Read-Host "Type 'RESTORE' to confirm"
if ($confirm -ne "RESTORE") {
    Write-Host "Restore cancelled." -ForegroundColor Cyan
    exit 0
}

Write-Host "Dropping and recreating database..." -ForegroundColor Cyan
docker exec $ContainerName psql -U $DbUser -d postgres -c "DROP DATABASE IF EXISTS $DbName;"
docker exec $ContainerName psql -U $DbUser -d postgres -c "CREATE DATABASE $DbName;"

# Copy dump into container and pg_restore
$TempDump = "/tmp/restore.dump"
docker cp $BackupFile "${ContainerName}:${TempDump}"
docker exec $ContainerName pg_restore -U $DbUser -d $DbName --no-owner --no-acl $TempDump 2>$null
$restoreExit = $LASTEXITCODE
docker exec $ContainerName rm -f $TempDump 2>$null

# pg_restore may exit 1 for non-fatal warnings (e.g. owner); 0 = success
if ($restoreExit -eq 0) {
    Write-Host "Restore completed successfully." -ForegroundColor Green
} else {
    Write-Host "Restore finished with exit code $restoreExit (may include non-fatal warnings)." -ForegroundColor Yellow
}

Write-Host "Run migrations if needed: docker compose -f docker-compose.prod.yml run --rm migrate" -ForegroundColor Cyan
