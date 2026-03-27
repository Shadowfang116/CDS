#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Phase 10: Verify OCR review, override, and rerun flow.

.DESCRIPTION
    Tests the OCR review endpoints:
    - GET OCR review
    - PATCH override
    - DELETE override
    - POST rerun

.PARAMETER ApiBaseUrl
    API base URL (default: http://localhost:8000).

.EXAMPLE
    .\scripts\dev\verify_ocr_review_flow.ps1
#>

param(
    [string]$ApiBaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHASE 10: OCR REVIEW FLOW VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Dev login
Write-Host "[1/7] Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@orga.com"
    org_name = "OrgA"
    role = "Admin"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json" -ErrorAction Stop
    $token = $loginResponse.access_token
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    Write-Host "[OK] Authenticated" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Authentication failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Find first case -> document -> page
Write-Host ""
Write-Host "[2/7] Finding test data..." -ForegroundColor Yellow

try {
    $cases = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases" -Method GET -Headers $headers -ErrorAction Stop
    if (-not $cases -or $cases.Count -eq 0) {
        Write-Host "[SKIP] No cases found. Skipping verification." -ForegroundColor Yellow
        exit 0
    }
    
    $caseId = $cases[0].id
    Write-Host "[OK] Found case: $caseId" -ForegroundColor Green
    
    $documents = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents" -Method GET -Headers $headers -ErrorAction Stop
    if (-not $documents -or $documents.Count -eq 0) {
        Write-Host "[SKIP] No documents found. Skipping verification." -ForegroundColor Yellow
        exit 0
    }
    
    $documentId = $documents[0].id
    Write-Host "[OK] Found document: $documentId" -ForegroundColor Green
    
    $pageNumber = 1
    Write-Host "[OK] Using page: $pageNumber" -ForegroundColor Green
    
} catch {
    Write-Host "[SKIP] Failed to find test data: $_" -ForegroundColor Yellow
    exit 0
}

# Step 3: GET OCR review
Write-Host ""
Write-Host "[3/7] GET OCR review..." -ForegroundColor Yellow

try {
    $reviewResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr" -Method GET -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] OCR review loaded" -ForegroundColor Green
    Write-Host "  - Page ID: $($reviewResponse.page_id)" -ForegroundColor White
    Write-Host "  - Source: $($reviewResponse.ocr.source)" -ForegroundColor White
    Write-Host "  - Has override: $($reviewResponse.ocr.has_override)" -ForegroundColor White
    Write-Host "  - Confidence: $($reviewResponse.ocr.confidence)" -ForegroundColor White
    
    $initialSource = $reviewResponse.ocr.source
    
} catch {
    Write-Host "[FAIL] GET OCR review failed: $_" -ForegroundColor Red
    exit 1
}

# Step 4: PATCH override
Write-Host ""
Write-Host "[4/7] PATCH override..." -ForegroundColor Yellow

try {
    $overrideBody = @{
        override_text = "TEST OVERRIDE - This is a test override for Phase 10 verification."
        reason = "Phase 10 verification test"
    } | ConvertTo-Json
    
    $overrideResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr" -Method PATCH -Body $overrideBody -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Override set" -ForegroundColor Green
    
    # Verify override
    $reviewAfterOverride = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr" -Method GET -Headers $headers -ErrorAction Stop
    
    if ($reviewAfterOverride.ocr.source -eq "override") {
        Write-Host "[PASS] Override verified - source is now 'override'" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Override not working - source is still '$($reviewAfterOverride.ocr.source)'" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "[FAIL] PATCH override failed: $_" -ForegroundColor Red
    exit 1
}

# Step 5: DELETE override
Write-Host ""
Write-Host "[5/7] DELETE override..." -ForegroundColor Yellow

try {
    $clearResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr" -Method DELETE -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Override cleared" -ForegroundColor Green
    
    # Verify override cleared
    $reviewAfterClear = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr" -Method GET -Headers $headers -ErrorAction Stop
    
    if ($reviewAfterClear.ocr.source -eq "ocr") {
        Write-Host "[PASS] Override cleared - source is now 'ocr'" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Override clear not working - source is still '$($reviewAfterClear.ocr.source)'" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "[FAIL] DELETE override failed: $_" -ForegroundColor Red
    exit 1
}

# Step 6: POST rerun
Write-Host ""
Write-Host "[6/7] POST rerun OCR..." -ForegroundColor Yellow

try {
    $rerunBody = @{
        force_profile = "enhanced"
    } | ConvertTo-Json
    
    $rerunResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/cases/$caseId/documents/$documentId/pages/$pageNumber/ocr/rerun" -Method POST -Body $rerunBody -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    if ($rerunResponse.queued) {
        Write-Host "[PASS] OCR rerun queued successfully" -ForegroundColor Green
        Write-Host "  - Task: $($rerunResponse.task)" -ForegroundColor White
        Write-Host "  - Page ID: $($rerunResponse.page_id)" -ForegroundColor White
    } else {
        Write-Host "[FAIL] OCR rerun not queued" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "[FAIL] POST rerun failed: $_" -ForegroundColor Red
    exit 1
}

# Step 7: Summary
Write-Host ""
Write-Host "[7/7] Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[PASS] All OCR review flow tests passed:" -ForegroundColor Green
Write-Host "  ✓ GET OCR review" -ForegroundColor Green
Write-Host "  ✓ PATCH override" -ForegroundColor Green
Write-Host "  ✓ DELETE override" -ForegroundColor Green
Write-Host "  ✓ POST rerun" -ForegroundColor Green
Write-Host ""
Write-Host "Phase 10 verification complete!" -ForegroundColor Green
Write-Host ""
