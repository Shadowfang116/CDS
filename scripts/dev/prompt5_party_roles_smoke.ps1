#!/usr/bin/env pwsh
# Prompt 5 Party Roles Smoke Test
# Runs extraction directly on stored OCR text without UI

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Context IDs
$SALE_DEED_DOC_ID = "8fa48b2d-c169-450e-8b16-8855b6a83def"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 5 PARTY ROLES SMOKE TEST" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "[OK] Docker engine is reachable" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Docker engine is not running" -ForegroundColor Red
    exit 1
}

# Step 2: Pull OCR text from database
Write-Host ""
Write-Host "[2/4] Pulling OCR text from database..." -ForegroundColor Yellow
$ocrQuery = @"
SELECT 
    page_number,
    ocr_text
FROM document_pages
WHERE document_id = '$SALE_DEED_DOC_ID'
ORDER BY page_number;
"@

$ocrResults = $ocrQuery | docker compose exec -T db psql -U bank_diligence -d bank_diligence -t -A -F "|" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Failed to query OCR text: $ocrResults" -ForegroundColor Red
    exit 1
}

# Parse OCR results into pages
$pages = @()
$currentPage = $null
$currentText = @()

foreach ($line in $ocrResults) {
    if ($line -match '^(\d+)\|(.+)$') {
        $pageNum = [int]$matches[1]
        $text = $matches[2]
        
        if ($currentPage -ne $null -and $currentPage -ne $pageNum) {
            $pages += @{
                page_number = $currentPage
                text = ($currentText -join "`n")
            }
            $currentText = @()
        }
        
        $currentPage = $pageNum
        $currentText += $text
    }
}

if ($currentPage -ne $null) {
    $pages += @{
        page_number = $currentPage
        text = ($currentText -join "`n")
    }
}

Write-Host "[OK] Retrieved $($pages.Count) pages" -ForegroundColor Green

# Step 3: Run extraction in API container
Write-Host ""
Write-Host "[3/4] Running party roles extraction..." -ForegroundColor Yellow

# Create Python script to run extraction
$pythonScript = @"
import sys
import json
from app.services.extractors.party_roles import extract_party_roles_from_document, PageOCR, is_plausible_person_name, clean_person_name

# Parse pages from JSON
pages_data = json.loads(sys.stdin.read())
pages = []
for p in pages_data:
    pages.append(PageOCR(
        document_id='$SALE_DEED_DOC_ID',
        document_name='sale_deed.pdf',
        page_number=p['page_number'],
        text=p['text']
    ))

# Extract roles
roles = extract_party_roles_from_document(pages)

# Test plausibility for each role
results = {
    'seller': {
        'raw': roles.get('seller_names', ''),
        'cleaned': clean_person_name(roles.get('seller_names', '')),
        'plausible': is_plausible_person_name(roles.get('seller_names', '')) if roles.get('seller_names') else False,
        'method': roles.get('evidence', {}).get('role_method', {}).get('seller', 'none')
    },
    'buyer': {
        'raw': roles.get('buyer_names', ''),
        'cleaned': clean_person_name(roles.get('buyer_names', '')),
        'plausible': is_plausible_person_name(roles.get('buyer_names', '')) if roles.get('buyer_names') else False,
        'method': roles.get('evidence', {}).get('role_method', {}).get('buyer', 'none')
    },
    'witness': {
        'raw': roles.get('witness_names', ''),
        'cleaned': clean_person_name(roles.get('witness_names', '')),
        'plausible': is_plausible_person_name(roles.get('witness_names', '')) if roles.get('witness_names') else False,
        'method': roles.get('evidence', {}).get('role_method', {}).get('witness', 'none')
    }
}

print(json.dumps(results, ensure_ascii=False, indent=2))
"@

# Convert pages to JSON
$pagesJson = $pages | ConvertTo-Json -Compress

# Run extraction
$extractionOutput = $pagesJson | docker compose exec -T api python $pythonScriptFile 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Extraction failed: $extractionOutput" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Extraction completed" -ForegroundColor Green

# Step 4: Print results
Write-Host ""
Write-Host "[4/4] Extraction Results:" -ForegroundColor Yellow
Write-Host ""
Write-Host $extractionOutput
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "END" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

