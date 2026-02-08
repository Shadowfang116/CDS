#!/usr/bin/env pwsh
# Pilot Real Case - Multi-Document Upload Script
# Usage: .\scripts\dev\pilot_real_case.ps1 -Title "DHA Pilot" -Paths @("doc1.pdf","doc2.pdf") -RunRules -GenerateExports

param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    
    [Parameter(Mandatory=$true)]
    [string[]]$Paths,
    
    [string]$Org = "OrgA",
    [string]$Role = "Admin",
    [int]$Days = 30,
    [switch]$ForceOcr = $false,
    [switch]$RunRules = $true,
    [switch]$GenerateExports = $true
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
Write-Host "PILOT REAL CASE - MULTI-DOCUMENT UPLOAD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate all files exist
$validFiles = @()
foreach ($path in $Paths) {
    if (-not (Test-Path $path)) {
        Write-Host "[FAIL] File not found: $path" -ForegroundColor Red
        exit 1
    }
    
    $fileInfo = Get-Item $path
    $fileExtension = $fileInfo.Extension.ToLower()
    
    # Validate file type
    $allowedExtensions = @('.pdf', '.docx', '.jpg', '.jpeg', '.png')
    if ($allowedExtensions -notcontains $fileExtension) {
        Write-Host "[FAIL] Unsupported file type: $fileExtension (file: $path)" -ForegroundColor Red
        Write-Host "Supported types: PDF, DOCX, JPG, PNG" -ForegroundColor Yellow
        exit 1
    }
    
    # Validate file size (50 MB limit for PDF/images, 25 MB for DOCX)
    $maxSizeMB = if ($fileExtension -eq '.docx') { 25 } else { 50 }
    $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    if ($fileSizeMB -gt $maxSizeMB) {
        Write-Host "[FAIL] File too large: ${fileSizeMB}MB (max: ${maxSizeMB}MB) - $path" -ForegroundColor Red
        exit 1
    }
    
    $validFiles += @{
        Path = $path
        Name = $fileInfo.Name
        SizeMB = $fileSizeMB
        Extension = $fileExtension
    }
}

Write-Host "Case Title: $Title" -ForegroundColor Green
Write-Host "Documents: $($validFiles.Count)" -ForegroundColor Green
foreach ($file in $validFiles) {
    Write-Host "  - $($file.Name) ($($file.SizeMB)MB)" -ForegroundColor Gray
}
Write-Host ""

# Check API health
Write-Host "[0/7] Checking API health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/deep" -Method GET -UseBasicParsing -ErrorAction Stop
    if ($healthResponse.StatusCode -ne 200) {
        throw "Health check returned status $($healthResponse.StatusCode)"
    }
    $healthData = $healthResponse.Content | ConvertFrom-Json
    if ($healthData.status -ne "ok") {
        Write-Host "[WARN]  API health check returned status: $($healthData.status)" -ForegroundColor Yellow
        Write-Host "  Continuing anyway..." -ForegroundColor Gray
    }
} catch {
    Write-Host "[FAIL] API health check failed: $_" -ForegroundColor Red
    Write-Host "Checking container status..." -ForegroundColor Yellow
    docker compose ps api
    Write-Host ""
    Write-Host "API logs:" -ForegroundColor Yellow
    docker compose logs api --tail=50
    exit 1
}
Write-Host "[OK] API healthy" -ForegroundColor Green

# Step 1: Dev login
Write-Host ""
Write-Host "[1/7] Authenticating..." -ForegroundColor Yellow
$loginEmail = if ($Org -eq "OrgA") { "admin@orga.com" } else { "admin@orgb.com" }
$loginBody = @{
    email = $loginEmail
    org_name = $Org
    role = $Role
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
Write-Host "[OK] Authenticated as $loginEmail ($Role)" -ForegroundColor Green

# Step 2: Create case
Write-Host ""
Write-Host "[2/7] Creating case..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Bearer $token"
}
$caseBody = @{
    title = $Title
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

# Step 3: Upload all documents
Write-Host ""
Write-Host "[3/7] Uploading documents..." -ForegroundColor Yellow
$docIds = @()
$uploadUrl = "http://localhost:8000/api/v1/cases/$caseId/documents"

foreach ($file in $validFiles) {
    try {
        $absolutePath = (Resolve-Path $file.Path).Path
        
        Write-Host "  Uploading: $($file.Name)..." -ForegroundColor Gray
        
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
        
        $docIds += $docId
        Write-Host "    [OK] Uploaded: $docId" -ForegroundColor Green
        
        # Wait for document to be split (check status)
        $maxSplitAttempts = 30
        $splitAttempt = 0
        $splitComplete = $false
        while ($splitAttempt -lt $maxSplitAttempts -and -not $splitComplete) {
            Start-Sleep -Seconds 1
            $splitAttempt++
            try {
                $docResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$docId" -Headers $headers -ErrorAction Stop
                $docStatus = $docResponse.status
                if ($docStatus -eq "Split" -or $docStatus -eq "Uploaded") {
                    if ($docResponse.page_count -gt 0) {
                        $splitComplete = $true
                    }
                } elseif ($docStatus -eq "Failed") {
                    if ($docResponse.page_count -gt 0) {
                        Write-Host "    [WARN]  Status Failed but pages exist, continuing..." -ForegroundColor Yellow
                        $splitComplete = $true
                    } else {
                        throw "Document split failed and no pages found"
                    }
                }
            } catch {
                # Continue polling
            }
        }
        if (-not $splitComplete) {
            Write-Host "    [WARN]  Document may still be processing, continuing..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    [FAIL] Upload failed for $($file.Name): $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[OK] All documents uploaded ($($docIds.Count) documents)" -ForegroundColor Green

# Step 4: Enqueue OCR for all documents and wait
Write-Host ""
Write-Host "[4/7] Enqueuing OCR for all documents..." -ForegroundColor Yellow
$forceFlag = if ($ForceOcr) { "true" } else { "false" }

foreach ($docId in $docIds) {
    try {
        $ocrResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr?force=$forceFlag" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        if ($ocrResponse.StatusCode -ne 200 -and $ocrResponse.StatusCode -ne 202) {
            $errorBody = $ocrResponse.Content | ConvertFrom-Json
            throw "OCR enqueue returned status $($ocrResponse.StatusCode): $($errorBody.detail)"
        }
        Write-Host "  [OK] OCR enqueued for document: $docId" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN]  Failed to enqueue OCR for $docId : $_" -ForegroundColor Yellow
        Write-Host "    Continuing with other documents..." -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Waiting for OCR completion (timeout: 240s per document)..." -ForegroundColor Yellow
$allCompleted = $true
$allFailed = $false
$failedDocs = @()

foreach ($docId in $docIds) {
    Write-Host "  Polling OCR status for document: $docId..." -ForegroundColor Gray
    $maxAttempts = 120  # 120 attempts * 2 seconds = 240 seconds
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
            }
            
            if ($attempt % 15 -eq 0) {
                Write-Host "    Status: Done=$doneCount/$totalPages, Processing=$processingCount, Failed=$failedCount" -ForegroundColor Gray
            }
        } catch {
            # Continue polling on error
        }
    }
    
    if ($failed) {
        Write-Host "  [FAIL] OCR failed for document: $docId" -ForegroundColor Red
        $allFailed = $true
        $failedDocs += $docId
    } elseif (-not $completed) {
        Write-Host "  [FAIL] OCR timeout for document: $docId" -ForegroundColor Red
        $allCompleted = $false
        $failedDocs += $docId
    } else {
        Write-Host "  [OK] OCR completed for document: $docId" -ForegroundColor Green
    }
}

if ($allFailed -or -not $allCompleted) {
    Write-Host ""
    Write-Host "[FAIL] OCR processing failed or timed out for documents: $($failedDocs -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] All OCR completed successfully" -ForegroundColor Green

# Step 5: Run rules evaluation
if ($RunRules) {
    Write-Host ""
    Write-Host "[5/7] Evaluating rules..." -ForegroundColor Yellow
    try {
        $rulesResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseId/evaluate" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        $rulesData = $rulesResponse.Content | ConvertFrom-Json
        
        $exceptionCount = if ($rulesData.exceptions) { $rulesData.exceptions.Count } else { 0 }
        $cpCount = if ($rulesData.cps) { $rulesData.cps.Count } else { 0 }
        
        Write-Host "[OK] Rules evaluated: $exceptionCount exceptions, $cpCount CPs" -ForegroundColor Green
    } catch {
        Write-Host "[WARN]  Rules evaluation failed: $_" -ForegroundColor Yellow
        Write-Host "  Continuing..." -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "[5/7] Skipping rules evaluation (RunRules=false)" -ForegroundColor Gray
}

# Step 6: Generate exports
if ($GenerateExports) {
    Write-Host ""
    Write-Host "[6/7] Generating exports..." -ForegroundColor Yellow
    
    # Discrepancy letter
    try {
        $discResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseId/drafts/discrepancy-letter" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        $discData = $discResponse.Content | ConvertFrom-Json
        Write-Host "  [OK] Discrepancy letter: $($discData.url)" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN]  Discrepancy letter failed: $_" -ForegroundColor Yellow
    }
    
    # Bank pack PDF
    try {
        $bankPackResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseId/exports/bank-pack" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        $bankPackData = $bankPackResponse.Content | ConvertFrom-Json
        Write-Host "  [OK] Bank pack PDF: $($bankPackData.url)" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN]  Bank pack PDF failed: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[6/7] Skipping export generation (GenerateExports=false)" -ForegroundColor Gray
}

# Step 7: Final summary
Write-Host ""
Write-Host "[7/7] Final summary..." -ForegroundColor Yellow

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] PILOT CASE CREATED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "REAL_CASE_ID=$caseId" -ForegroundColor White
Write-Host "REAL_DOC_IDS=$($docIds -join ',')" -ForegroundColor White
Write-Host ""
Write-Host "Open URL: http://localhost:3000/cases/$caseId" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open Documents tab - verify OCR text" -ForegroundColor Gray
Write-Host "  2. Check Exceptions/CPs tab - review DHA rules" -ForegroundColor Gray
Write-Host "  3. Go to Reports tab - generate exports" -ForegroundColor Gray
Write-Host ""

