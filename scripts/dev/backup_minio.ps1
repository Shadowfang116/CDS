# Bank Diligence Platform - MinIO Backup Script (PowerShell)
# Uses mc (MinIO Client) to mirror bucket contents to local directory

param(
    [string]$BackupDir = ".\backups\minio",
    [string]$MinioAlias = "local",
    [string]$Bucket = "case-files"
)

$ErrorActionPreference = "Stop"

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupDir $Timestamp

Write-Host "Starting MinIO backup..." -ForegroundColor Cyan
Write-Host "Backup directory: $BackupPath"

# Check if mc is installed
$mcExists = Get-Command mc -ErrorAction SilentlyContinue
if (-not $mcExists) {
    Write-Host "MinIO Client (mc) not found. Installing via scoop..." -ForegroundColor Yellow
    Write-Host "Please install mc manually: https://min.io/download#/windows" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing mc, configure it with:" -ForegroundColor Cyan
    Write-Host "  mc alias set $MinioAlias http://localhost:9000 minioadmin change_me" -ForegroundColor White
    exit 1
}

# Check if alias is configured
$aliasCheck = mc alias list $MinioAlias 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "MinIO alias '$MinioAlias' not configured." -ForegroundColor Yellow
    Write-Host "Configure it with:" -ForegroundColor Cyan
    Write-Host "  mc alias set $MinioAlias http://localhost:9000 minioadmin change_me" -ForegroundColor White
    exit 1
}

# Mirror the bucket
Write-Host "Mirroring bucket: $Bucket" -ForegroundColor Cyan
mc mirror "$MinioAlias/$Bucket" "$BackupPath/$Bucket" --overwrite

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backup completed successfully!" -ForegroundColor Green
    
    # Count files
    $FileCount = (Get-ChildItem -Recurse -File $BackupPath | Measure-Object).Count
    Write-Host "Files backed up: $FileCount"
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nBackup complete. Files saved to: $BackupPath" -ForegroundColor Cyan

