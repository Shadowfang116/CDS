# Ops: MinIO restore from a backup directory (from backup_minio.ps1 mc mirror or extracted volume zip).
# Run from repo root.

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    [string]$MinioAlias = "local",
    [string]$Bucket = "case-files"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupPath)) {
    Write-Host "Backup path not found: $BackupPath" -ForegroundColor Red
    exit 1
}

Write-Host "=== WARNING ===" -ForegroundColor Yellow
Write-Host "This will overwrite objects in MinIO bucket '$Bucket'." -ForegroundColor Yellow
$confirm = Read-Host "Type 'RESTORE' to confirm"
if ($confirm -ne "RESTORE") {
    Write-Host "Restore cancelled." -ForegroundColor Cyan
    exit 0
}

$mcExists = Get-Command mc -ErrorAction SilentlyContinue
if (-not $mcExists) {
    Write-Host "MinIO Client (mc) not found." -ForegroundColor Red
    exit 1
}

$SourcePath = $BackupPath
if (Test-Path (Join-Path $BackupPath $Bucket)) {
    $SourcePath = Join-Path $BackupPath $Bucket
}

Write-Host "Restoring from $SourcePath to $MinioAlias/$Bucket" -ForegroundColor Cyan
mc mirror "$SourcePath" "$MinioAlias/$Bucket" --overwrite

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore completed successfully." -ForegroundColor Green
} else {
    Write-Host "Restore failed." -ForegroundColor Red
    exit 1
}
