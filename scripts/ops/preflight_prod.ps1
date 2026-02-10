# Preflight checks for production deployment. Run from repo root.
$ErrorActionPreference = "Continue"
$failed = $false

Write-Host "=== Preflight (production) ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[FAIL] Docker not found." -ForegroundColor Red
    $failed = $true
} else { Write-Host "[OK] Docker present" -ForegroundColor Green }

$null = docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] docker compose not available." -ForegroundColor Red
    $failed = $true
} else { Write-Host "[OK] docker compose present" -ForegroundColor Green }

$envPath = Join-Path (Get-Location) ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "[FAIL] .env not found. Copy from .env.prod.example and set secrets." -ForegroundColor Red
    $failed = $true
} else { Write-Host "[OK] .env exists" -ForegroundColor Green }

$envVars = @{}
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $envVars[$matches[1]] = $matches[2].Trim()
        }
    }
}

$appEnv = $envVars["APP_ENV"]
if ($appEnv -ne "production") {
    Write-Host "[WARN] APP_ENV is '$appEnv'; should be 'production' for prod." -ForegroundColor Yellow
} else { Write-Host "[OK] APP_ENV=production" -ForegroundColor Green }

$checks = @(
    @("POSTGRES_PASSWORD", 12),
    @("APP_SECRET_KEY", 32),
    @("MINIO_ROOT_PASSWORD", 12)
)
foreach ($c in $checks) {
    $name = $c[0]; $minLen = $c[1]
    $val = $envVars[$name]
    if (-not $val) {
        Write-Host "[FAIL] $name is missing." -ForegroundColor Red
        $failed = $true
    } elseif ($val -match "REPLACE_ME|change_me|^$") {
        Write-Host "[FAIL] $name looks like a placeholder." -ForegroundColor Red
        $failed = $true
    } elseif ($appEnv -eq "production" -and $val.Length -lt $minLen) {
        Write-Host "[WARN] $name shorter than $minLen chars." -ForegroundColor Yellow
    } else { Write-Host "[OK] $name set" -ForegroundColor Green }
}

Write-Host ""
Write-Host "Ports (3000, 8000, 9000, 9001):" -ForegroundColor Cyan
foreach ($p in @(3000, 8000, 9000, 9001)) {
    try {
        $conn = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $p)
        $conn.Close(); Write-Host "  $p in use" -ForegroundColor Yellow
    } catch { Write-Host "  $p free" -ForegroundColor Gray }
}

Write-Host ""
if ($failed) { Write-Host "Preflight FAILED." -ForegroundColor Red; exit 1 }
Write-Host "Preflight PASSED. Run: docker compose -f docker-compose.prod.yml up -d --build" -ForegroundColor Green
exit 0
