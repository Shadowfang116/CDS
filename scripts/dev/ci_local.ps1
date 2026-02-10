# Phase 6: Run CI pipeline locally (lint, typecheck, build, Docker build, API smoke).
# Usage: from repo root, .\scripts\dev\ci_local.ps1
# Or: cd bank-diligence-platform; .\scripts\dev\ci_local.ps1
$ErrorActionPreference = "Stop"

$RepoRoot = if ($PSScriptRoot) {
    $scriptsDir = Split-Path $PSScriptRoot -Parent
    Split-Path $scriptsDir -Parent
} else {
    (Get-Location).Path
}
Set-Location $RepoRoot

$failed = $false

# 1) Frontend: lint, typecheck, build
Write-Host "`n[ci_local] --- Frontend: lint, typecheck, build ---" -ForegroundColor Cyan
$frontendDir = Join-Path $RepoRoot "frontend"
if (-not (Test-Path $frontendDir)) {
    Write-Error "frontend directory not found at $frontendDir"
}
Push-Location $frontendDir
try {
    npm ci
    npm run lint
    npm run typecheck
    npm run build
} catch {
    Write-Host "[ci_local] Frontend failed: $_" -ForegroundColor Red
    $failed = $true
} finally {
    Pop-Location
}

if ($failed) {
    Write-Host "[ci_local] Stopping after frontend failure." -ForegroundColor Red
    exit 1
}

# 2) Docker: build api and frontend
Write-Host "`n[ci_local] --- Docker: build api, frontend ---" -ForegroundColor Cyan
try {
    docker compose build api frontend
} catch {
    Write-Host "[ci_local] Docker build failed: $_" -ForegroundColor Red
    exit 1
}

# 3) API smoke (PowerShell version for Windows)
Write-Host "`n[ci_local] --- API smoke ---" -ForegroundColor Cyan
$smokeScript = Join-Path $RepoRoot "scripts" "ci" "api_smoke.ps1"
if (-not (Test-Path $smokeScript)) {
    Write-Host "[ci_local] Smoke script not found: $smokeScript" -ForegroundColor Red
    exit 1
}
& $smokeScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ci_local] API smoke failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n[ci_local] All checks passed." -ForegroundColor Green
exit 0
