# Collect diagnostics bundle for support. Run from repo root.
# Creates .\diagnostics\<timestamp>\ with compose status, logs, health, migrations status.
# Resilient: if a step fails, continue and note the failure.

param(
    [string]$ComposeFile = "docker-compose.prod.yml",
    [string]$ApiBase = "http://localhost:8000",
    [string]$AdminToken = "",
    [string]$OrgId = ""
)

$ErrorActionPreference = "Continue"
$root = Get-Location
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $root "diagnostics"
$runDir = Join-Path $outDir $timestamp

if (-not (Test-Path $runDir)) {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
}

Write-Host "Collecting diagnostics to $runDir" -ForegroundColor Cyan

function SafeRun($name, $scriptBlock) {
    try {
        & $scriptBlock | Out-File -FilePath (Join-Path $runDir $name) -Encoding utf8
        Write-Host "  [OK] $name" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $name - $($_.Exception.Message)" -ForegroundColor Red
        "[FAILED] $($_.Exception.Message)" | Out-File -FilePath (Join-Path $runDir $name) -Encoding utf8
    }
}

# Compose status
SafeRun "compose_ps.txt" { docker compose -f $script:ComposeFile ps -a 2>&1 }

# Logs (tail 300)
SafeRun "logs_api.txt" { docker compose -f $script:ComposeFile logs api --tail=300 2>&1 }
SafeRun "logs_migrate.txt" { docker compose -f $script:ComposeFile logs migrate --tail=300 2>&1 }
$workerLog = Join-Path $runDir "logs_worker.txt"
try {
    docker compose -f $ComposeFile logs worker --tail=300 2>&1 | Out-File -FilePath $workerLog -Encoding utf8
    Write-Host "  [OK] logs_worker.txt" -ForegroundColor Green
} catch {
    "Worker service not present or failed: $($_.Exception.Message)" | Out-File -FilePath $workerLog -Encoding utf8
    Write-Host "  [SKIP] logs_worker.txt (no worker or error)" -ForegroundColor Yellow
}

# Health deep
$healthFile = Join-Path $runDir "health_deep.json"
try {
    $response = Invoke-WebRequest -Uri "$ApiBase/api/v1/health/deep" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    $response.Content | Out-File -FilePath $healthFile -Encoding utf8
    Write-Host "  [OK] health_deep.json" -ForegroundColor Green
} catch {
    "Request failed: $($_.Exception.Message)" | Out-File -FilePath $healthFile -Encoding utf8
    Write-Host "  [FAIL] health_deep.json" -ForegroundColor Red
}

# Migrations status (admin-only; skip if no token)
$migrationsFile = Join-Path $runDir "admin_migrations_status.json"
if ($AdminToken -and $OrgId) {
    try {
        $headers = @{
            "Authorization" = "Bearer $AdminToken"
            "X-Org-Id"     = $OrgId
        }
        $response = Invoke-WebRequest -Uri "$ApiBase/api/v1/admin/migrations/status" -Headers $headers -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        $response.Content | Out-File -FilePath $migrationsFile -Encoding utf8
        Write-Host "  [OK] admin_migrations_status.json" -ForegroundColor Green
    } catch {
        "Request failed: $($_.Exception.Message)" | Out-File -FilePath $migrationsFile -Encoding utf8
        Write-Host "  [FAIL] admin_migrations_status.json" -ForegroundColor Red
    }
} else {
    "Skipped (no AdminToken or OrgId). Pass -AdminToken and -OrgId to include." | Out-File -FilePath $migrationsFile -Encoding utf8
    Write-Host "  [SKIP] admin_migrations_status.json (no token/org)" -ForegroundColor Yellow
}

# Build info (admin-only)
$buildInfoFile = Join-Path $runDir "admin_build_info.json"
if ($AdminToken -and $OrgId) {
    try {
        $headers = @{
            "Authorization" = "Bearer $AdminToken"
            "X-Org-Id"     = $OrgId
        }
        $response = Invoke-WebRequest -Uri "$ApiBase/api/v1/admin/build-info" -Headers $headers -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        $response.Content | Out-File -FilePath $buildInfoFile -Encoding utf8
        Write-Host "  [OK] admin_build_info.json" -ForegroundColor Green
    } catch {
        "Request failed (endpoint may not exist): $($_.Exception.Message)" | Out-File -FilePath $buildInfoFile -Encoding utf8
        Write-Host "  [SKIP] admin_build_info.json" -ForegroundColor Yellow
    }
} else {
    "Skipped (no AdminToken or OrgId)." | Out-File -FilePath $buildInfoFile -Encoding utf8
}

# README for support
$readme = @"
Diagnostics bundle collected at $timestamp.
Attach this folder to your support ticket.

Contents:
- compose_ps.txt    : docker compose ps -a
- logs_api.txt      : api logs (tail 300)
- logs_migrate.txt  : migrate logs (tail 300)
- logs_worker.txt   : worker logs if present
- health_deep.json  : GET /api/v1/health/deep
- admin_migrations_status.json : GET /api/v1/admin/migrations/status (if token provided)
- admin_build_info.json        : GET /api/v1/admin/build-info (if token provided)
"@
$readme | Out-File -FilePath (Join-Path $runDir "README.txt") -Encoding utf8

Write-Host ""
Write-Host "Done. Output: $runDir" -ForegroundColor Green
Write-Host "Attach this folder to your support ticket." -ForegroundColor Cyan
