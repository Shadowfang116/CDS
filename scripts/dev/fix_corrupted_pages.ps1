#!/usr/bin/env pwsh
# Fix Corrupted Pages Script - P17
# Repairs/re-OCRs corrupted pages for a specific document
# Usage: ./scripts/dev/fix_corrupted_pages.ps1 -DocumentId <DOC_ID> [-ForceReOCR]

param(
    [Parameter(Mandatory=$false)]
    [string]$DocumentId = "8fa48b2d-c169-450e-8b16-8855b6a83def",  # Default: SALE_DEED_DOC_ID
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceReOCR = $false  # If true, force re-OCR even if not corrupted
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FIX CORRUPTED PAGES - P17" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    docker ps | Out-Null
} catch {
    Write-Host "[FAIL] Docker not available" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker available" -ForegroundColor Green

# Step 2: Authenticate
Write-Host ""
Write-Host "[2/4] Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@orga.com"
    org_name = "OrgA"
    role = "Admin"
} | ConvertTo-Json

$token = $null
$maxRetries = 5
$retryCount = 0

while ($retryCount -lt $maxRetries -and -not $token) {
    try {
        Start-Sleep -Seconds 2
        $loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
        $loginData = $loginResponse.Content | ConvertFrom-Json
        $token = $loginData.access_token
    } catch {
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Write-Host "[FAIL] Authentication failed: $_" -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 2
    }
}

if (-not $token) {
    Write-Host "[FAIL] Could not get access token" -ForegroundColor Red
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
}

Write-Host "[OK] Authenticated" -ForegroundColor Green

# Step 3: Get document info and check for corrupted pages
Write-Host ""
Write-Host "[3/4] Checking document pages for corruption..." -ForegroundColor Yellow

# Query for pages with mojibake characters
$mojibakeQuery = @"
SELECT 
    dp.page_number,
    dp.ocr_engine,
    dp.ocr_confidence,
    CASE 
        WHEN dp.ocr_engine LIKE '%repaired%' THEN 'REPAIRED'
        WHEN dp.ocr_engine LIKE '%urd_fallback%' OR dp.ocr_engine LIKE '%urd+eng%' THEN 'RE_OCRED'
        ELSE 'ORIGINAL'
    END AS ocr_status,
    LENGTH(dp.ocr_text) AS text_length,
    LEFT(dp.ocr_text, 100) AS ocr_text_preview
FROM document_pages dp
WHERE dp.document_id = '$DocumentId'
  AND dp.ocr_text IS NOT NULL
ORDER BY dp.page_number;
"@

$pagesInfo = $mojibakeQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1

Write-Host "[OK] Retrieved page info" -ForegroundColor Green

# Step 4: Force re-run autofill to trigger fallback for corrupted pages
Write-Host ""
Write-Host "[4/4] Triggering autofill to repair corrupted pages..." -ForegroundColor Yellow

# Get case_id for the document
$caseQuery = @"
SELECT case_id FROM documents WHERE id = '$DocumentId';
"@
$caseResult = $caseQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A 2>&1
$caseId = $caseResult.Trim()

if (-not $caseId -or $caseId -match "error|ERROR") {
    Write-Host "[FAIL] Could not find case_id for document $DocumentId" -ForegroundColor Red
    Write-Host "Result: $caseResult" -ForegroundColor Red
    exit 1
}

Write-Host "Case ID: $caseId" -ForegroundColor Cyan
Write-Host "Document ID: $DocumentId" -ForegroundColor Cyan

# Trigger autofill which will call get_page_text_with_fallback for each page
try {
    $autofillUrl = "http://localhost:8000/api/v1/cases/$caseId/dossier/autofill?overwrite=true"
    $autofillResponse = Invoke-WebRequest -Uri $autofillUrl -Method POST -Headers $headers -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] Autofill triggered (this will repair corrupted pages)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Autofill failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Wait a moment for processing
Start-Sleep -Seconds 5

# Query again to see repair status
Write-Host ""
Write-Host "Checking repair status..." -ForegroundColor Yellow
$afterQuery = @"
SELECT 
    dp.page_number,
    dp.ocr_engine,
    dp.ocr_confidence,
    CASE 
        WHEN dp.ocr_engine LIKE '%repaired%' THEN 'REPAIRED'
        WHEN dp.ocr_engine LIKE '%urd_fallback%' OR dp.ocr_engine LIKE '%urd+eng%' THEN 'RE_OCRED'
        ELSE 'ORIGINAL'
    END AS ocr_status,
    LENGTH(dp.ocr_text) AS text_length,
    LEFT(dp.ocr_text, 100) AS ocr_text_preview
FROM document_pages dp
WHERE dp.document_id = '$DocumentId'
  AND dp.ocr_text IS NOT NULL
ORDER BY dp.page_number;
"@

$afterInfo = $afterQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence 2>&1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BEFORE:" -ForegroundColor Yellow
Write-Host $pagesInfo
Write-Host ""
Write-Host "AFTER:" -ForegroundColor Yellow
Write-Host $afterInfo
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "[OK] Fix corrupted pages complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: If pages still show corruption, check logs for OCR_FALLBACK messages:" -ForegroundColor Yellow
Write-Host "  docker compose logs api --tail=100 | Select-String 'OCR_FALLBACK'" -ForegroundColor Gray
