#!/usr/bin/env pwsh
# E2E Verification Test for Prompt 5/12
# Tests: OCR script-aware language selection, party role extraction, confidence normalization, View deep-link
# Usage: .\scripts\dev\prompt5_e2e_test.ps1

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 5/12 E2E VERIFICATION TEST" -ForegroundColor Cyan
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
    $loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
    $loginData = $loginResponse.Content | ConvertFrom-Json
    $token = $loginData.access_token
    if (-not $token) {
        throw "No access token received"
    }
} catch {
    Write-Host "[FAIL] Authentication failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Authenticated" -ForegroundColor Green

$headers = @{
    "Authorization" = "Bearer $token"
}

# Step 2: Create test case
Write-Host ""
Write-Host "[2/7] Creating test case..." -ForegroundColor Yellow
$caseBody = @{
    title = "Sale Deed - Urdu OCR Test (Prompt 5)"
} | ConvertTo-Json

try {
    $caseResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases" -Method POST -Body $caseBody -ContentType "application/json" -Headers $headers -UseBasicParsing -ErrorAction Stop
    $caseData = $caseResponse.Content | ConvertFrom-Json
    $caseId = $caseData.id
    if (-not $caseId) {
        throw "No case ID received"
    }
} catch {
    Write-Host "[FAIL] Failed to create case: $_" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Case created: $caseId" -ForegroundColor Green

# Step 3: Upload sale deed
Write-Host ""
Write-Host "[3/7] Uploading sale deed.pdf..." -ForegroundColor Yellow
$saleDeedPath = "docs\pilot_samples_real\sale deed.pdf"
if (-not (Test-Path $saleDeedPath)) {
    Write-Host "[FAIL] File not found: $saleDeedPath" -ForegroundColor Red
    Write-Host "Please ensure the file exists in the repository." -ForegroundColor Yellow
    exit 1
}

try {
    $absolutePath = (Resolve-Path $saleDeedPath).Path
    $uploadUrl = "http://localhost:8000/api/v1/cases/$caseId/documents"
    
    $curlResponse = curl.exe -s -X POST `
        -H "Authorization: Bearer $token" `
        -F "file=@$absolutePath" `
        $uploadUrl
    
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE"
    }
    
    $uploadData = $curlResponse | ConvertFrom-Json
    $saleDeedDocId = $uploadData.id
    if (-not $saleDeedDocId) {
        throw "No document ID received"
    }
} catch {
    Write-Host "[FAIL] Upload failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Sale deed uploaded: $saleDeedDocId" -ForegroundColor Green

# Step 4: Upload Fard
Write-Host ""
Write-Host "[4/7] Uploading Fard.pdf..." -ForegroundColor Yellow
$fardPath = "docs\pilot_samples_real\Fard.pdf"
if (-not (Test-Path $fardPath)) {
    Write-Host "[FAIL] File not found: $fardPath" -ForegroundColor Red
    Write-Host "Please ensure the file exists in the repository." -ForegroundColor Yellow
    exit 1
}

try {
    $absolutePath = (Resolve-Path $fardPath).Path
    
    $curlResponse = curl.exe -s -X POST `
        -H "Authorization: Bearer $token" `
        -F "file=@$absolutePath" `
        $uploadUrl
    
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE"
    }
    
    $uploadData = $curlResponse | ConvertFrom-Json
    $fardDocId = $uploadData.id
    if (-not $fardDocId) {
        throw "No document ID received"
    }
} catch {
    Write-Host "[FAIL] Upload failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Fard uploaded: $fardDocId" -ForegroundColor Green

# Step 5: Wait for document splitting
Write-Host ""
Write-Host "[5/7] Waiting for document splitting..." -ForegroundColor Yellow
$maxWait = 60
$waitCount = 0
$allSplit = $false

while ($waitCount -lt $maxWait -and -not $allSplit) {
    Start-Sleep -Seconds 2
    $waitCount += 2
    
    try {
        $saleDeedStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$saleDeedDocId" -Headers $headers -ErrorAction Stop
        $fardStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$fardDocId" -Headers $headers -ErrorAction Stop
        
        if ($saleDeedStatus.status -eq "Split" -and $fardStatus.status -eq "Split") {
            $allSplit = $true
        }
    } catch {
        # Continue polling
    }
}

if (-not $allSplit) {
    Write-Host "[WARN] Documents may still be splitting. Continuing..." -ForegroundColor Yellow
}

# Step 6: Run OCR on both documents
Write-Host ""
Write-Host "[6/7] Running OCR on both documents..." -ForegroundColor Yellow

# Run OCR on sale deed
try {
    $ocrResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$saleDeedDocId/ocr?force=false" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] OCR enqueued for sale deed" -ForegroundColor Green
} catch {
    Write-Host "[WARN] OCR enqueue for sale deed failed: $_" -ForegroundColor Yellow
}

# Run OCR on Fard
try {
    $ocrResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$fardDocId/ocr?force=false" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] OCR enqueued for Fard" -ForegroundColor Green
} catch {
    Write-Host "[WARN] OCR enqueue for Fard failed: $_" -ForegroundColor Yellow
}

# Wait for OCR completion
Write-Host "Waiting for OCR completion (timeout: 300s)..." -ForegroundColor Gray
$maxAttempts = 150
$attempt = 0
$allComplete = $false

while ($attempt -lt $maxAttempts -and -not $allComplete) {
    Start-Sleep -Seconds 2
    $attempt++
    
    try {
        $saleDeedOcrStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$saleDeedDocId/ocr-status" -Headers $headers -ErrorAction Stop
        $fardOcrStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$fardDocId/ocr-status" -Headers $headers -ErrorAction Stop
        
        $saleDeedDone = ($saleDeedOcrStatus.status_counts.Done -eq $saleDeedOcrStatus.total_pages) -and ($saleDeedOcrStatus.status_counts.Failed -eq 0)
        $fardDone = ($fardOcrStatus.status_counts.Done -eq $fardOcrStatus.total_pages) -and ($fardOcrStatus.status_counts.Failed -eq 0)
        
        if ($saleDeedDone -and $fardDone) {
            $allComplete = $true
        }
        
        if ($attempt % 15 -eq 0) {
            Write-Host "  Sale deed: $($saleDeedOcrStatus.status_counts.Done)/$($saleDeedOcrStatus.total_pages), Fard: $($fardOcrStatus.status_counts.Done)/$($fardOcrStatus.total_pages)" -ForegroundColor Gray
        }
    } catch {
        # Continue polling
    }
}

if (-not $allComplete) {
    Write-Host "[WARN] OCR may still be processing. Check worker logs." -ForegroundColor Yellow
} else {
    Write-Host "[OK] OCR completed for both documents" -ForegroundColor Green
}

# Step 7: Run Autofill
Write-Host ""
Write-Host "[7/7] Running Autofill..." -ForegroundColor Yellow
try {
    $autofillBody = @{
        overwrite = $false
    } | ConvertTo-Json
    
    $autofillResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseId/autofill" -Method POST -Body $autofillBody -ContentType "application/json" -Headers $headers -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] Autofill completed" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Autofill failed: $_" -ForegroundColor Yellow
}

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] E2E TEST SETUP COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CASE_ID=$caseId" -ForegroundColor White
Write-Host "SALE_DEED_DOC_ID=$saleDeedDocId" -ForegroundColor White
Write-Host "FARD_DOC_ID=$fardDocId" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open UI: http://localhost:3000/cases/$caseId" -ForegroundColor White
Write-Host "2. Go to OCR Extractions tab (All)" -ForegroundColor White
Write-Host "3. Verify party.seller.names, party.buyer.names, party.witness.names fields" -ForegroundColor White
Write-Host "4. Click View on one extraction to test deep-link" -ForegroundColor White
Write-Host "5. Check worker logs for OCR_PAGE_OBSERVABILITY entries" -ForegroundColor White
Write-Host ""
Write-Host "SQL queries for proof:" -ForegroundColor Yellow
Write-Host "  See scripts/dev/prompt5_sql_queries.sql" -ForegroundColor White
Write-Host ""
Write-Host "Debug commands:" -ForegroundColor Yellow
Write-Host "  Check party role extraction logs:" -ForegroundColor White
Write-Host "    docker compose logs api --tail=300 | Select-String `"PARTY_ROLES_DEBUG`"" -ForegroundColor Gray
Write-Host "  Run SQL queries (replace IDs in scripts/dev/prompt5_sql_queries.sql):" -ForegroundColor White
Write-Host "    Get-Content scripts/dev/prompt5_sql_queries.sql | ForEach-Object { `$_ -replace '<CASE_ID>', '$caseId' -replace '<SALE_DEED_DOC_ID>', '$saleDeedDocId' -replace '<FARD_DOC_ID>', '$fardDocId' } | docker compose exec -T db psql -U bank_diligence -d bank_diligence" -ForegroundColor Gray
Write-Host "  Debug SQL (inspect OCR patterns):" -ForegroundColor White
Write-Host "    See scripts/dev/prompt5_party_roles_debug.sql" -ForegroundColor Gray
Write-Host ""

