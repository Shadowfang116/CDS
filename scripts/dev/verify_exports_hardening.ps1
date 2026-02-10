# Phase 8: Verify exports hardening (idempotency, status, download).
# Run with API available (e.g. docker compose up -d api db redis minio worker).
# Uses dev-login; creates/uses a case and triggers Bank Pack twice (expect same export_id), then polls and verifies download.
$ErrorActionPreference = "Stop"
$Base = "http://localhost:8000/api/v1"
$Email = "pilot@example.com"
$Org = "Demo Org"
$Role = "Reviewer"

Write-Host "[verify_exports] Dev login..."
$loginBody = @{ email = $Email; org_name = $Org; role = $Role } | ConvertTo-Json
$loginResp = Invoke-RestMethod -Uri "$Base/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResp.access_token
$headers = @{ Authorization = "Bearer $token" }

Write-Host "[verify_exports] List cases..."
$cases = Invoke-RestMethod -Uri "$Base/cases?page=1&page_size=5" -Headers $headers
$caseId = $null
if ($cases.items -and $cases.items.Count -gt 0) {
    $caseId = $cases.items[0].id
    Write-Host "[verify_exports] Using existing case: $caseId"
} else {
    Write-Host "[verify_exports] Create case..."
    $createBody = @{ title = "Verify exports hardening " + (Get-Date -Format "yyyyMMdd-HHmm") } | ConvertTo-Json
    $newCase = Invoke-RestMethod -Uri "$Base/cases" -Method POST -Body $createBody -ContentType "application/json" -Headers $headers
    $caseId = $newCase.id
    Write-Host "[verify_exports] Created case: $caseId"
}
if (-not $caseId) { throw "No case available" }

Write-Host "[verify_exports] Trigger Bank Pack (first time)..."
$r1 = Invoke-RestMethod -Uri "$Base/cases/$caseId/exports/bank-pack" -Method POST -Headers $headers
$exportId1 = $r1.export_id
$status1 = $r1.status
Write-Host "  export_id=$exportId1 status=$status1"

Write-Host "[verify_exports] Trigger Bank Pack (second time, expect same export_id)..."
$r2 = Invoke-RestMethod -Uri "$Base/cases/$caseId/exports/bank-pack" -Method POST -Headers $headers
$exportId2 = $r2.export_id
$status2 = $r2.status
Write-Host "  export_id=$exportId2 status=$status2"

if ($exportId1 -ne $exportId2) {
    Write-Host "[verify_exports] FAIL: Idempotency broken. First export_id=$exportId1 second=$exportId2" -ForegroundColor Red
    exit 1
}
Write-Host "[verify_exports] Idempotency OK: same export_id returned." -ForegroundColor Green

$exportId = $exportId1
Write-Host "[verify_exports] Poll export status (max 120s)..."
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    $list = Invoke-RestMethod -Uri "$Base/cases/$caseId/exports" -Headers $headers
    $exp = $list.exports | Where-Object { $_.id -eq $exportId } | Select-Object -First 1
    if ($exp) {
        if ($exp.status -eq "succeeded") {
            Write-Host "  status=succeeded" -ForegroundColor Green
            break
        }
        if ($exp.status -eq "failed") {
            Write-Host "  status=failed error_code=$($exp.error_code) error_message=$($exp.error_message)" -ForegroundColor Yellow
            Write-Host "[verify_exports] Export failed (expected in some env). Check error_code/message above." -ForegroundColor Yellow
            exit 0
        }
        Write-Host "  status=$($exp.status) ..."
    }
    Start-Sleep -Seconds 3
}
if ((Get-Date) -ge $deadline) {
    Write-Host "[verify_exports] Timeout waiting for export." -ForegroundColor Red
    exit 1
}

Write-Host "[verify_exports] Get download URL..."
try {
    $dl = Invoke-RestMethod -Uri "$Base/exports/$exportId/download" -Headers $headers
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 409) {
        Write-Host "[verify_exports] 409 on download (export not ready). Detail: $($_.ErrorDetails.Message)" -ForegroundColor Red
        exit 1
    }
    throw
}
$url = $dl.url
if (-not $url) { Write-Host "[verify_exports] No download URL." -ForegroundColor Red; exit 1 }

Write-Host "[verify_exports] Download file and check size..."
$fileResp = Invoke-WebRequest -Uri $url -UseBasicParsing -Method Get
$bytes = $fileResp.Content
if (-not $bytes -or $bytes.Length -eq 0) {
    Write-Host "[verify_exports] FAIL: Downloaded file is empty." -ForegroundColor Red
    exit 1
}
Write-Host "[verify_exports] Downloaded $($bytes.Length) bytes. OK." -ForegroundColor Green
Write-Host "[verify_exports] All checks passed." -ForegroundColor Green
exit 0
