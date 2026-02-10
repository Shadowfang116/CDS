# Ops: MinIO backup. Uses mc mirror if available; otherwise zips a local minio_data path.
# Run from repo root. For mc: configure alias first, e.g. mc alias set local http://localhost:9000 minioadmin <password>

param(
    [string]$BackupDir = ".\backups\minio",
    [string]$MinioAlias = "local",
    [string]$Bucket = "case-files",
    [string]$VolumePath = ""   # If set, zip this path instead of using mc (e.g. Docker volume mount)
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupDir $Timestamp

if ($VolumePath) {
    # Option B: zip volume directory
    if (-not (Test-Path $VolumePath)) {
        Write-Host "Volume path not found: $VolumePath" -ForegroundColor Red
        exit 1
    }
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    $ZipFile = Join-Path $BackupDir "minio_$Timestamp.zip"
    Compress-Archive -Path "$VolumePath\*" -DestinationPath $ZipFile -Force
    Write-Host "MinIO backup (volume zip): $ZipFile" -ForegroundColor Green
    exit 0
}

# Option A: mc mirror
$mcExists = Get-Command mc -ErrorAction SilentlyContinue
if (-not $mcExists) {
    Write-Host "MinIO Client (mc) not found. Install from https://min.io/download or set -VolumePath to backup MinIO data directory." -ForegroundColor Red
    exit 1
}

$aliasCheck = mc alias list $MinioAlias 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "MinIO alias '$MinioAlias' not configured. Run: mc alias set $MinioAlias http://localhost:9000 <user> <password>" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
Write-Host "MinIO backup (mc mirror): $Bucket -> $BackupPath" -ForegroundColor Cyan
mc mirror "$MinioAlias/$Bucket" "$BackupPath/$Bucket" --overwrite

if ($LASTEXITCODE -eq 0) {
    $FileCount = (Get-ChildItem -Recurse -File $BackupPath -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "Backup completed: $FileCount files in $BackupPath" -ForegroundColor Green
} else {
    Write-Host "Backup failed." -ForegroundColor Red
    exit 1
}
