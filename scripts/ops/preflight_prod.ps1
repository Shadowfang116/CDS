# Preflight checks for production deployment. Run from repo root.
$ErrorActionPreference = "Continue"
$failed = $false
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$verifyScript = Join-Path $scriptDir "verify_prod_readiness.ps1"

Write-Host "=== Preflight (production) ===" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $verifyScript)) {
    Write-Host "[FAIL] verify_prod_readiness.ps1 not found." -ForegroundColor Red
    exit 1
}

& $verifyScript
if ($LASTEXITCODE -ne 0) {
    $failed = $true
}

Write-Host ""
Write-Host "Ports (3000, 8000, 9000, 9001):" -ForegroundColor Cyan
foreach ($p in @(3000, 8000, 9000, 9001)) {
    try {
        $conn = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $p)
        $conn.Close()
        Write-Host "  $p in use" -ForegroundColor Yellow
    } catch {
        Write-Host "  $p free" -ForegroundColor Gray
    }
}

Write-Host ""
if ($failed) {
    Write-Host "Preflight FAILED." -ForegroundColor Red
    exit 1
}

Write-Host "Preflight PASSED. Run: docker compose -f docker-compose.prod.yml up -d --build" -ForegroundColor Green
exit 0
