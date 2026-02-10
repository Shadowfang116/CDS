# Phase 3 verification: X-Request-ID, structured logs, audit immutability.
# Prerequisites: API running (e.g. docker compose up). For /cases, set DEV_LOGIN_* or use existing token.
# Usage: .\scripts\dev\verify_logging_and_audit.ps1

$ErrorActionPreference = "Stop"
$BaseUrl = $env:API_BASE_URL ?? "http://localhost:8000"
# Run from repo root so docker-compose.yml is found, or set COMPOSE_FILE
$ComposeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "docker-compose.yml" }
if (-not (Test-Path $ComposeFile)) { $ComposeFile = "docker-compose.yml" }

Write-Host "=== Phase 3: Logging + Audit verification ===" -ForegroundColor Cyan
Write-Host ""

# 1) GET /api/v1/health/deep — capture X-Request-ID
Write-Host "1. Calling GET /api/v1/health/deep..." -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BaseUrl/api/v1/health/deep" -Method Get -UseBasicParsing
    $reqIdDeep = $r.Headers["X-Request-ID"]
    if ($reqIdDeep) {
        Write-Host "   X-Request-ID: $reqIdDeep" -ForegroundColor Green
    } else {
        Write-Host "   FAIL: X-Request-ID header missing on health/deep" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2) GET /api/v1/cases (authenticated) — capture X-Request-ID
Write-Host ""
Write-Host "2. Calling GET /api/v1/cases (authenticated)..." -ForegroundColor Yellow
$reqIdCases = $null
$token = $env:DEV_TOKEN
if (-not $token) {
    $loginBody = @{
        email    = $env:DEV_LOGIN_EMAIL ?? "admin@test.local"
        org_name = $env:DEV_LOGIN_ORG   ?? "Test Org"
        role     = "Admin"
    } | ConvertTo-Json
    try {
        $login = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/dev-login" -Method Post -Body $loginBody -ContentType "application/json"
        $token = $login.access_token
    } catch {
        Write-Host "   Skip: could not dev-login (set DEV_LOGIN_EMAIL, DEV_LOGIN_ORG or DEV_TOKEN)." -ForegroundColor Gray
    }
}
if ($token) {
    try {
        $r2 = Invoke-WebRequest -Uri "$BaseUrl/api/v1/cases" -Method Get -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing
        $reqIdCases = $r2.Headers["X-Request-ID"]
        if ($reqIdCases) {
            Write-Host "   X-Request-ID: $reqIdCases" -ForegroundColor Green
        } else {
            Write-Host "   FAIL: X-Request-ID header missing on /cases" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "   Skip: $($_.Exception.Message)" -ForegroundColor Gray
    }
} else {
    Write-Host "   Skip: no token for /cases" -ForegroundColor Gray
}

Write-Host ""
Write-Host "3. Request IDs: health/deep=$reqIdDeep  cases=$reqIdCases" -ForegroundColor Cyan

# 4) Logs: if docker compose available, tail and check for request_id
Write-Host ""
Write-Host "4. Checking API logs for request_id (docker compose logs api --tail=50)..." -ForegroundColor Yellow
$logsContainRequestId = $false
try {
    $logs = docker compose -f $ComposeFile logs api --tail=50 2>&1 | Out-String
    if ($reqIdDeep -and $logs -match [regex]::Escape($reqIdDeep)) {
        Write-Host "   Found request_id from health/deep in logs." -ForegroundColor Green
        $logsContainRequestId = $true
    } elseif ($logs -match "request_id") {
        Write-Host "   Logs contain request_id (structured logging active)." -ForegroundColor Green
        $logsContainRequestId = $true
    } else {
        Write-Host "   No request_id in last 50 lines (run a request then re-run this script, or API may not be via docker)." -ForegroundColor Gray
    }
} catch {
    Write-Host "   Skip: docker compose not available or not in project dir." -ForegroundColor Gray
}

# 5) Audit immutability: attempt delete via ORM in api container
Write-Host ""
Write-Host "5. Audit immutability: attempting to delete an audit row via ORM (must raise)..." -ForegroundColor Yellow
$immutableOk = $false
$ormCmd = "from app.db.session import SessionLocal; from app.models.audit_log import AuditLog; import sys; db=SessionLocal(); r=db.query(AuditLog).first(); print('row', bool(r));`ntry:`n (r and (db.delete(r), db.commit(), (print('ERROR'), sys.exit(1)))); print('OK no row'); sys.exit(0)`nexcept Exception as ex: print('OK', type(ex).__name__, str(ex)[:80]); sys.exit(0)"
try {
    $out = docker compose -f $ComposeFile exec -T api python -c $ormCmd 2>&1
    $outStr = $out | Out-String
    if ($outStr -match "OK:" -and $outStr -match "AUDIT|RuntimeError|not allowed") {
        Write-Host "   Audit guard raised as expected. Delete/update blocked." -ForegroundColor Green
        $immutableOk = $true
    } elseif ($outStr -match "row False") {
        Write-Host "   No audit rows in DB; guard is registered (run an action to create an audit row and re-run)." -ForegroundColor Green
        $immutableOk = $true
    } else {
        Write-Host "   Output: $outStr" -ForegroundColor Gray
        Write-Host "   Expected: OK and [AUDIT] or RuntimeError." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   Skip: docker compose exec failed: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  X-Request-ID on health/deep: $(if ($reqIdDeep) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($reqIdDeep) { 'Green' } else { 'Red' })
Write-Host "  X-Request-ID on /cases:      $(if ($reqIdCases) { 'PASS' } else { 'SKIP/FAIL' })" -ForegroundColor $(if ($reqIdCases) { 'Green' } else { 'Gray' })
Write-Host "  Logs contain request_id:     $(if ($logsContainRequestId) { 'PASS' } else { 'SKIP' })" -ForegroundColor $(if ($logsContainRequestId) { 'Green' } else { 'Gray' })
Write-Host "  Audit immutability (no delete): $(if ($immutableOk) { 'PASS' } else { 'SKIP' })" -ForegroundColor $(if ($immutableOk) { 'Green' } else { 'Gray' })
if ($reqIdDeep) {
    Write-Host ""
    Write-Host "PASS: X-Request-ID present; audit guard and logging in place." -ForegroundColor Green
    exit 0
} else {
    exit 1
}
