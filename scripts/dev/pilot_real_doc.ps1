#!/usr/bin/env pwsh
# Pilot Real Document Upload Script
# Usage: .\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\sample_scanned.pdf"

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Helper function for content type
function Get-ContentType {
    param([string]$ext)
    switch ($ext) {
        '.pdf' { return 'application/pdf' }
        '.docx' { return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }
        '.jpg' { return 'image/jpeg' }
        '.jpeg' { return 'image/jpeg' }
        '.png' { return 'image/png' }
        default { return 'application/octet-stream' }
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PILOT REAL DOCUMENT UPLOAD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate file exists
if (-not (Test-Path $Path)) {
    Write-Host "[FAIL] File not found: $Path" -ForegroundColor Red
    Write-Host "Please provide a valid file path." -ForegroundColor Yellow
    exit 1
}

$fileInfo = Get-Item $Path
$fileName = $fileInfo.Name
$fileExtension = $fileInfo.Extension.ToLower()

# Validate file type
$allowedExtensions = @('.pdf', '.docx', '.jpg', '.jpeg', '.png')
if ($allowedExtensions -notcontains $fileExtension) {
    Write-Host "[FAIL] Unsupported file type: $fileExtension" -ForegroundColor Red
    Write-Host "Supported types: PDF, DOCX, JPG, PNG" -ForegroundColor Yellow
    exit 1
}

# Validate file size (50 MB limit for PDF/images, 25 MB for DOCX)
$maxSizeMB = if ($fileExtension -eq '.docx') { 25 } else { 50 }
$fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
if ($fileSizeMB -gt $maxSizeMB) {
    Write-Host "[FAIL] File too large: ${fileSizeMB}MB (max: ${maxSizeMB}MB)" -ForegroundColor Red
    exit 1
}

Write-Host "File: $fileName (${fileSizeMB}MB)" -ForegroundColor Green
Write-Host ""

# Step 1: Dev login
Write-Host "[1/5] Authenticating..." -ForegroundColor Yellow
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

# Step 2: Create case
Write-Host ""
Write-Host "[2/5] Creating test case..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$caseTitle = "REAL DOC TEST - $timestamp"

$headers = @{
    "Authorization" = "Bearer $token"
}
$caseBody = @{
    title = $caseTitle
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

# Step 3: Upload document
Write-Host ""
Write-Host "[3/5] Uploading document..." -ForegroundColor Yellow
try {
    # Use curl.exe for reliable multipart upload
    $uploadUrl = "http://localhost:8000/api/v1/cases/$caseId/documents"
    $absolutePath = (Resolve-Path $Path).Path
    
    $curlResponse = curl.exe -s -X POST `
        -H "Authorization: Bearer $token" `
        -F "file=@$absolutePath" `
        $uploadUrl
    
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed with exit code $LASTEXITCODE"
    }
    
    $uploadData = $curlResponse | ConvertFrom-Json
    $docId = $uploadData.id
    if (-not $docId) {
        throw "No document ID received. Response: $curlResponse"
    }
} catch {
    Write-Host "[FAIL] Upload failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Document uploaded: $docId" -ForegroundColor Green

# Wait for document to be split (check status)
Write-Host "Waiting for document processing..." -ForegroundColor Gray
$maxSplitAttempts = 30
$splitAttempt = 0
$splitComplete = $false
$docStatus = "Unknown"
while ($splitAttempt -lt $maxSplitAttempts -and -not $splitComplete) {
    Start-Sleep -Seconds 1
    $splitAttempt++
    try {
        $docResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$docId" -Headers $headers -ErrorAction Stop
        $docStatus = $docResponse.status
        if ($docStatus -eq "Split") {
            $splitComplete = $true
        } elseif ($docStatus -eq "Failed") {
            Write-Host "[WARN]  Document split failed, but checking if pages exist..." -ForegroundColor Yellow
            # Check if pages exist despite failed status
            if ($docResponse.page_count -gt 0) {
                Write-Host "  Pages exist ($($docResponse.page_count)), continuing..." -ForegroundColor Gray
                $splitComplete = $true
            } else {
                Write-Host "[FAIL] Document split failed and no pages found" -ForegroundColor Red
                Write-Host "  Check worker logs: docker compose logs worker --tail=100" -ForegroundColor Yellow
                exit 1
            }
        }
    } catch {
        # Continue polling
    }
}
if (-not $splitComplete) {
    Write-Host "[WARN]  Document status: $docStatus (may still be processing)" -ForegroundColor Yellow
    Write-Host "  Continuing with OCR attempt..." -ForegroundColor Gray
}

# Step 4: Enqueue OCR
Write-Host ""
Write-Host "[4/5] Enqueuing OCR..." -ForegroundColor Yellow
try {
    $ocrResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr?force=false" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
    if ($ocrResponse.StatusCode -ne 200 -and $ocrResponse.StatusCode -ne 202) {
        $errorBody = $ocrResponse.Content | ConvertFrom-Json
        throw "OCR enqueue returned status $($ocrResponse.StatusCode): $($errorBody.detail)"
    }
} catch {
    Write-Host "[FAIL] Failed to enqueue OCR: $_" -ForegroundColor Red
    Write-Host "Note: Document must be in 'Split' status. Check document status in UI." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] OCR enqueued" -ForegroundColor Green

# Step 5: Wait for OCR completion
Write-Host ""
Write-Host "[5/5] Waiting for OCR completion (timeout: 180s)..." -ForegroundColor Yellow
$maxAttempts = 90  # 90 attempts * 2 seconds = 180 seconds
$attempt = 0
$completed = $false
$failed = $false

while ($attempt -lt $maxAttempts -and -not $completed -and -not $failed) {
    Start-Sleep -Seconds 2
    $attempt++
    
    try {
        $statusResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr-status" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
        $statusData = $statusResponse.Content | ConvertFrom-Json
        
        $totalPages = $statusData.total_pages
        $statusCounts = $statusData.status_counts
        $doneCount = if ($statusCounts.PSObject.Properties.Name -contains "Done") { $statusCounts.Done } else { 0 }
        $failedCount = if ($statusCounts.PSObject.Properties.Name -contains "Failed") { $statusCounts.Failed } else { 0 }
        $processingCount = if ($statusCounts.PSObject.Properties.Name -contains "Processing") { $statusCounts.Processing } else { 0 }
        
        if ($doneCount -eq $totalPages -and $failedCount -eq 0) {
            $completed = $true
        } elseif ($failedCount -gt 0) {
            $failed = $true
            Write-Host "[FAIL] OCR failed: $failedCount pages failed" -ForegroundColor Red
            if ($statusData.failed_pages) {
                foreach ($failedPage in $statusData.failed_pages) {
                    Write-Host "  Page $($failedPage.page_number): $($failedPage.error)" -ForegroundColor Red
                }
            }
        }
        
        if ($attempt % 10 -eq 0) {
            Write-Host "  Status: Done=$doneCount/$totalPages, Processing=$processingCount, Failed=$failedCount (attempt $attempt/$maxAttempts)" -ForegroundColor Gray
        }
    } catch {
        # Continue polling on error
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "[FAIL] OCR processing failed" -ForegroundColor Red
    exit 1
}

if (-not $completed) {
    Write-Host ""
    Write-Host "[FAIL] OCR did not complete within 180 seconds" -ForegroundColor Red
    exit 1
}

# Get final status for metrics
try {
    $finalStatus = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr-status" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
    $finalData = $finalStatus.Content | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "[OK] OCR completed successfully!" -ForegroundColor Green
    if ($finalData.average_ocr_chars_per_page) {
        Write-Host "  Avg chars/page: $([math]::Round($finalData.average_ocr_chars_per_page, 0))" -ForegroundColor Gray
    }
    if ($finalData.processing_seconds) {
        Write-Host "  Processing time: $([math]::Round($finalData.processing_seconds, 1))s" -ForegroundColor Gray
    }
} catch {
    # Ignore metrics errors
}

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] UPLOAD COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "REAL_CASE_ID=$caseId" -ForegroundColor White
Write-Host "REAL_DOC_ID=$docId" -ForegroundColor White
Write-Host ""
Write-Host "Open URL: http://localhost:3000/cases/$caseId" -ForegroundColor Yellow
Write-Host ""

