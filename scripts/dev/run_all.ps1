#!/usr/bin/env pwsh
# Run all pilot scripts in correct order
# Usage: .\scripts\dev\run_all.ps1

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PILOT FULL RUN - Bank Diligence Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script runs: reset -> smoke_test -> pilot_uat" -ForegroundColor Yellow
Write-Host ""

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Step 1: Reset
Write-Host "[1/3] Running pilot_reset.ps1..." -ForegroundColor Yellow
& "$scriptRoot\pilot_reset.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] pilot_reset.ps1 failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 2: Smoke tests
Write-Host ""
Write-Host "[2/3] Running smoke_test.ps1..." -ForegroundColor Yellow
& "$scriptRoot\smoke_test.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] smoke_test.ps1 failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 3: UAT
Write-Host ""
Write-Host "[3/3] Running pilot_uat.ps1..." -ForegroundColor Yellow
& "$scriptRoot\pilot_uat.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] pilot_uat.ps1 failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[OK] All scripts completed successfully!" -ForegroundColor Green
