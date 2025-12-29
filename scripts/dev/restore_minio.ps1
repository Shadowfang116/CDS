# Bank Diligence Platform - MinIO Restore Script (PowerShell)
# Restores MinIO bucket from local backup directory

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
Write-Host "This will overwrite objects in the MinIO bucket '$Bucket'." -ForegroundColor Yellow
Write-Host "Existing objects with the same keys will be replaced!" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Type 'RESTORE' to confirm"

if ($confirm -ne "RESTORE") {
    Write-Host "Restore cancelled." -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Starting MinIO restore..." -ForegroundColor Cyan
Write-Host "Backup path: $BackupPath"

# Check if mc is installed
$mcExists = Get-Command mc -ErrorAction SilentlyContinue
if (-not $mcExists) {
    Write-Host "MinIO Client (mc) not found." -ForegroundColor Red
    exit 1
}

# Determine source path
$SourcePath = $BackupPath
if (Test-Path "$BackupPath\$Bucket") {
    $SourcePath = "$BackupPath\$Bucket"
}

# Mirror back to MinIO
Write-Host "Restoring to bucket: $Bucket" -ForegroundColor Cyan
mc mirror "$SourcePath" "$MinioAlias/$Bucket" --overwrite

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Restore failed!" -ForegroundColor Red
    exit 1
}

