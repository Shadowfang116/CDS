# Ops: PostgreSQL backup (pg_dump custom format). Produces a timestamped .dump file.
# Run from repo root. Requires db container running.

param(
    [string]$BackupDir = ".\backups\postgres",
    [string]$ContainerName = "bank-diligence-platform-db-1",
    [string]$DbUser = "bank_diligence",
    [string]$DbName = "bank_diligence"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "bank_diligence_$Timestamp.dump"

Write-Host "PostgreSQL backup (custom format)..." -ForegroundColor Cyan
Write-Host "Container: $ContainerName -> $BackupFile"

$TempInContainer = "/tmp/backup.dump"
docker exec $ContainerName pg_dump -U $DbUser -d $DbName -Fc -f $TempInContainer
if ($LASTEXITCODE -ne 0) {
    Write-Host "pg_dump failed." -ForegroundColor Red
    exit 1
}
docker cp "${ContainerName}:${TempInContainer}" $BackupFile
docker exec $ContainerName rm -f $TempInContainer 2>$null

if (Test-Path $BackupFile) {
    $FileSize = (Get-Item $BackupFile).Length / 1MB
    Write-Host "Backup completed: $BackupFile ($([math]::Round($FileSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "Copy out of container failed." -ForegroundColor Red
    exit 1
}
