#!/usr/bin/env pwsh
# Pilot UAT Runner - Comprehensive end-to-end test for pilot readiness
# Usage: .\scripts\dev\pilot_uat.ps1
# ASCII-only; save as UTF-8 with BOM

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CmdCapture {
  param(
    [Parameter(Mandatory=$true)][string]$Command,
    [string]$FailMessage = "Command failed"
  )
  # Use cmd.exe so PowerShell does not treat stderr as error records.
  $outputLines = & cmd.exe /c "$Command 2>&1"
  $exit = $LASTEXITCODE
  $output = ($outputLines -join "`n").Trim()
  return [pscustomobject]@{ ExitCode = $exit; Output = $output; Command = $Command; FailMessage = $FailMessage }
}

function Assert-Ok {
  param([Parameter(Mandatory=$true)]$Result)
  if ($Result.ExitCode -ne 0) {
    Write-Host "[FAIL] $($Result.FailMessage)" -ForegroundColor Red
    Write-Host "Command: $($Result.Command)" -ForegroundColor Red
    if ($Result.Output) { Write-Host $Result.Output -ForegroundColor Red }
    exit $Result.ExitCode
  }
}

$uatStartTime = Get-Date
$uatArtifacts = @{
    start_time = $uatStartTime.ToString("yyyy-MM-dd HH:mm:ss")
    demo_case_id = $null
    demo_doc_id = $null
    real_case_id = $null
    real_doc_ids = @()
    exports = @()
    kpis = @{}
    audit_log_count = 0
    errors = @()
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PILOT UAT RUNNER - Phase P12" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================================================
# STEP 1: RESET + HEALTH CHECK
# ========================================================================
Write-Host "[1/6] Running reset and health checks..." -ForegroundColor Yellow
Write-Host ""

# Run pilot_reset
Write-Host "  Executing pilot_reset.ps1..." -ForegroundColor Gray
try {
    & .\scripts\dev\pilot_reset.ps1 -KeepVolumes
    if ($LASTEXITCODE -ne 0) {
        throw "pilot_reset.ps1 failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "[FAIL] Reset failed: $_" -ForegroundColor Red
    $uatArtifacts.errors += "Reset failed: $_"
    exit 1
}
Write-Host "[OK] Reset complete" -ForegroundColor Green

# Verify health
Write-Host "  Verifying health endpoint..." -ForegroundColor Gray
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/deep" -Method GET -UseBasicParsing -ErrorAction Stop
    if ($healthResponse.StatusCode -ne 200) {
        throw "Health check returned $($healthResponse.StatusCode)"
    }
    $healthData = $healthResponse.Content | ConvertFrom-Json
    if ($healthData.status -ne "ok") {
        throw "Health status is not 'ok'"
    }
} catch {
    Write-Host "[FAIL] Health check failed: $_" -ForegroundColor Red
    $uatArtifacts.errors += "Health check failed: $_"
    exit 1
}
Write-Host "[OK] Health check passed" -ForegroundColor Green

# Run smoke tests
Write-Host "  Running smoke tests..." -ForegroundColor Gray
try {
    & .\scripts\dev\smoke_test.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_test.ps1 failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "[FAIL] Smoke tests failed: $_" -ForegroundColor Red
    $uatArtifacts.errors += "Smoke tests failed: $_"
    exit 1
}
Write-Host "[OK] Smoke tests passed" -ForegroundColor Green

# ========================================================================
# STEP 2: DEMO DETERMINISTIC SCENARIO
# ========================================================================
Write-Host ""
Write-Host "[2/6] Running demo deterministic scenario..." -ForegroundColor Yellow
Write-Host ""

# Login
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
    $uatArtifacts.errors += "Authentication failed: $_"
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
}

# Get demo case ID (from seed output or first case)
Write-Host "  Finding demo case..." -ForegroundColor Gray
try {
    $casesResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
    $casesData = $casesResponse.Content | ConvertFrom-Json
    $demoCase = $casesData | Select-Object -First 1
    if (-not $demoCase) {
        throw "No cases found. Seed may have failed."
    }
    $uatArtifacts.demo_case_id = $demoCase.id
    Write-Host "  [OK] Demo case: $($demoCase.id)" -ForegroundColor Green
    
    # Get demo document
    $docsResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$($demoCase.id)/documents" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
    $docsData = $docsResponse.Content | ConvertFrom-Json
    if ($docsData.Count -gt 0) {
        $uatArtifacts.demo_doc_id = $docsData[0].id
        Write-Host "  [OK] Demo document: $($docsData[0].id)" -ForegroundColor Green
    }
} catch {
    Write-Host "[FAIL] Failed to find demo case: $_" -ForegroundColor Red
    $uatArtifacts.errors += "Demo case lookup failed: $_"
}

Write-Host "[OK] Demo scenario ready" -ForegroundColor Green

# ========================================================================
# STEP 3: REAL-DOC SUITE (if PDFs exist)
# ========================================================================
Write-Host ""
Write-Host "[3/6] Running real-doc suite..." -ForegroundColor Yellow
Write-Host ""

$realDocsPath = "docs\pilot_samples_real"
$realDocs = @()

if (Test-Path $realDocsPath) {
    # P13: Scan for both PDF and DOCX files
    $realPdfs = Get-ChildItem -Path $realDocsPath -Filter "*.pdf" -ErrorAction SilentlyContinue
    $realDocx = Get-ChildItem -Path $realDocsPath -Filter "*.docx" -ErrorAction SilentlyContinue
    $realDocs = @($realPdfs) + @($realDocx)
}

if ($realDocs.Count -eq 0) {
    Write-Host "  [WARN] No real documents (PDF/DOCX) found in $realDocsPath" -ForegroundColor Yellow
    Write-Host "  Skipping real-doc suite. Add PDFs or DOCX files to run full UAT." -ForegroundColor Gray
    Write-Host ""
    Write-Host "  To run real-doc suite:" -ForegroundColor Cyan
    Write-Host "    1. Place PDFs or DOCX files in docs/pilot_samples_real/" -ForegroundColor White
    Write-Host "    2. Re-run: .\scripts\dev\pilot_uat.ps1" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  Found $($realDocs.Count) document(s) in $realDocsPath" -ForegroundColor Green
    $pdfCount = ($realDocs | Where-Object { $_.Extension -eq '.pdf' }).Count
    $docxCount = ($realDocs | Where-Object { $_.Extension -eq '.docx' }).Count
    if ($pdfCount -gt 0) {
        Write-Host "    - $pdfCount PDF(s)" -ForegroundColor Gray
    }
    if ($docxCount -gt 0) {
        Write-Host "    - $docxCount DOCX file(s)" -ForegroundColor Gray
    }
    
    # Create real-doc case
    $realCaseTitle = ('PILOT REAL DOC CASE - {0:yyyy-MM-dd HH:mm:ss}' -f $uatStartTime)
    $caseBody = @{
        title = $realCaseTitle
    } | ConvertTo-Json
    
    try {
        $caseResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases" -Method POST -Body $caseBody -ContentType "application/json" -Headers $headers -UseBasicParsing -ErrorAction Stop
        $caseData = $caseResponse.Content | ConvertFrom-Json
        $uatArtifacts.real_case_id = $caseData.id
        Write-Host "  [OK] Created case: $($caseData.id)" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Failed to create real-doc case: $_" -ForegroundColor Red
        $uatArtifacts.errors += "Real-doc case creation failed: $_"
        exit 1
    }
    
    # Upload all documents (PDFs and DOCX)
    Write-Host "  Uploading $($realDocs.Count) document(s)..." -ForegroundColor Gray
    $uploadUrl = "http://localhost:8000/api/v1/cases/$($uatArtifacts.real_case_id)/documents"
    
    foreach ($doc in $realDocs) {
        try {
            $absolutePath = $doc.FullName
            Write-Host "    Uploading: $($doc.Name)..." -ForegroundColor Gray
            
            $curlResponse = curl.exe -s -X POST `
                -H "Authorization: Bearer $token" `
                -F "file=@$absolutePath" `
                $uploadUrl
            
            if ($LASTEXITCODE -ne 0) {
                throw "Upload failed for $($pdf.Name)"
            }
            
            $uploadData = $curlResponse | ConvertFrom-Json
            $docId = $uploadData.id
            $uatArtifacts.real_doc_ids += $docId
            Write-Host "      [OK] Uploaded: $docId" -ForegroundColor Green
            
            # Wait for split
            $maxSplitAttempts = 30
            $splitAttempt = 0
            while ($splitAttempt -lt $maxSplitAttempts) {
                Start-Sleep -Seconds 1
                $splitAttempt++
                try {
                    $docResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/$docId" -Headers $headers -ErrorAction Stop
                    if ($docResponse.page_count -gt 0) {
                        break
                    }
                } catch {
                    # Continue polling
                }
            }
        } catch {
            Write-Host "    [FAIL] Upload failed for $($doc.Name): $_" -ForegroundColor Red
            $uatArtifacts.errors += "Upload failed for $($doc.Name): $_"
        }
    }
    
    # Enqueue OCR for all documents
    Write-Host "  Enqueuing OCR..." -ForegroundColor Gray
    foreach ($docId in $uatArtifacts.real_doc_ids) {
        try {
            Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr?force=false" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop | Out-Null
        } catch {
            Write-Host "    [WARN] Failed to enqueue OCR for $docId" -ForegroundColor Yellow
        }
    }
    
    # Wait for OCR completion (with quality reporting)
    Write-Host "  Waiting for OCR completion (timeout: 180s per doc)..." -ForegroundColor Gray
    $allOcrComplete = $true
    
    foreach ($docId in $uatArtifacts.real_doc_ids) {
        $maxAttempts = 90  # 90 * 2s = 180s
        $attempt = 0
        $completed = $false
        
        while ($attempt -lt $maxAttempts -and -not $completed) {
            Start-Sleep -Seconds 2
            $attempt++
            
            try {
                $statusResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/$docId/ocr-status" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
                $statusData = $statusResponse.Content | ConvertFrom-Json
                
                $totalPages = $statusData.total_pages
                $statusCounts = $statusData.status_counts
                $doneCount = if ($statusCounts.PSObject.Properties.Name -contains "Done") { $statusCounts.Done } else { 0 }
                $failedCount = if ($statusCounts.PSObject.Properties.Name -contains "Failed") { $statusCounts.Failed } else { 0 }
                
                if ($doneCount -eq $totalPages -and $failedCount -eq 0) {
                    $completed = $true
                    
                    # Report quality
                    $qualityLevel = $statusData.quality_level
                    $qualityReasons = $statusData.quality_reasons
                    Write-Host "      [OK] OCR complete: $docId (Quality: $qualityLevel)" -ForegroundColor Green
                    if ($qualityLevel -ne "Good" -and $qualityReasons) {
                        Write-Host "        Quality reasons: $($qualityReasons -join ', ')" -ForegroundColor Yellow
                    }
                } elseif ($failedCount -gt 0) {
                    Write-Host "      [FAIL] OCR failed: $docId ($failedCount pages failed)" -ForegroundColor Red
                    $allOcrComplete = $false
                    break
                }
                
                if ($attempt % 15 -eq 0) {
                    Write-Host "        Status: $doneCount/$totalPages done" -ForegroundColor Gray
                }
            } catch {
                # Continue polling
            }
        }
        
        if (-not $completed) {
            Write-Host "      [FAIL] OCR timeout: $docId" -ForegroundColor Red
            $allOcrComplete = $false
        }
    }
    
    if (-not $allOcrComplete) {
        Write-Host "  [WARN] Some OCR jobs did not complete. Continuing..." -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] All OCR completed" -ForegroundColor Green
    }
}

# ========================================================================
# STEP 4: RULES + CONTROLS
# ========================================================================
Write-Host ""
Write-Host "[4/6] Executing rules + controls..." -ForegroundColor Yellow
Write-Host ""

$caseIdToUse = if ($uatArtifacts.real_case_id) { $uatArtifacts.real_case_id } else { $uatArtifacts.demo_case_id }

if ($caseIdToUse) {
    # Evaluate rules
    try {
        $evalResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseIdToUse/evaluate" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK] Rules evaluated" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Rules evaluation failed: $_" -ForegroundColor Yellow
    }
    
    # Get controls
    try {
        $controlsResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseIdToUse/controls" -Method GET -Headers $headers -UseBasicParsing -ErrorAction Stop
        $controlsData = $controlsResponse.Content | ConvertFrom-Json
        
        $uatArtifacts.kpis.regime = $controlsData.regime.regime
        $uatArtifacts.kpis.risk_label = $controlsData.risk.label
        $uatArtifacts.kpis.readiness_ready = $controlsData.readiness.ready
        $uatArtifacts.kpis.readiness_blockers = $controlsData.readiness.blockers
        
        Write-Host "  [OK] Controls retrieved" -ForegroundColor Green
        Write-Host "    Regime: $($controlsData.regime.regime)" -ForegroundColor Gray
        Write-Host "    Risk: $($controlsData.risk.label)" -ForegroundColor Gray
        Write-Host "    Ready: $($controlsData.readiness.ready)" -ForegroundColor Gray
    } catch {
        Write-Host "  [WARN] Controls retrieval failed: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] No case available for rules/controls" -ForegroundColor Yellow
}

# ========================================================================
# STEP 5: GENERATE EXPORTS
# ========================================================================
Write-Host ""
Write-Host "[5/6] Generating exports..." -ForegroundColor Yellow
Write-Host ""

if ($caseIdToUse) {
    # Bank Pack PDF
    try {
        $bankPackResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseIdToUse/exports/bank-pack" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        $bankPackData = $bankPackResponse.Content | ConvertFrom-Json
        $uatArtifacts.exports += @{
            type = "bank_pack_pdf"
            url = $bankPackData.url
            filename = $bankPackData.filename
            expires_at = $bankPackData.expires_at
        }
        Write-Host "  [OK] Bank Pack PDF: $($bankPackData.url)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Bank Pack PDF failed: $_" -ForegroundColor Red
        $uatArtifacts.errors += "Bank Pack PDF failed: $_"
    }
    
    # Discrepancy Letter DOCX
    try {
        $discResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/cases/$caseIdToUse/drafts/discrepancy-letter" -Method POST -Headers $headers -UseBasicParsing -ErrorAction Stop
        $discData = $discResponse.Content | ConvertFrom-Json
        $uatArtifacts.exports += @{
            type = "discrepancy_letter_docx"
            url = $discData.url
            filename = $discData.filename
            expires_at = $discData.expires_at
        }
        Write-Host "  [OK] Discrepancy Letter DOCX: $($discData.url)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Discrepancy Letter DOCX failed: $_" -ForegroundColor Red
        $uatArtifacts.errors += "Discrepancy Letter DOCX failed: $_"
    }
    
    # Cohort export (optional - for high severity filter)
    try {
        $cohortResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/exports/cohort?severity=high" -Method POST -Headers $headers -UseBasicParsing -ErrorAction SilentlyContinue
        if ($cohortResponse.StatusCode -eq 200) {
            $cohortData = $cohortResponse.Content | ConvertFrom-Json
            $uatArtifacts.exports += @{
                type = "cohort_csv"
                url = $cohortData.url
                filename = $cohortData.filename
            }
            Write-Host "  [OK] Cohort CSV: $($cohortData.url)" -ForegroundColor Green
        }
    } catch {
        # Cohort export is optional
    }
} else {
    Write-Host "  [WARN] No case available for exports" -ForegroundColor Yellow
}

# ========================================================================
# STEP 6: AUDIT LOG COUNT
# ========================================================================
Write-Host ""
Write-Host "[6/6] Checking audit log..." -ForegroundColor Yellow
Write-Host ""

try {
    $auditResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/audit?limit=1" -Method GET -Headers $headers -UseBasicParsing -ErrorAction SilentlyContinue
    if ($auditResponse.StatusCode -eq 200) {
        $auditData = $auditResponse.Content | ConvertFrom-Json
        $uatArtifacts.audit_log_count = $auditData.Count
        Write-Host "  [OK] Audit log entries: $($auditData.Count)" -ForegroundColor Green
    } else {
        # Fallback to database query
        $dbCheck = Invoke-CmdCapture -Command "docker compose exec -T db psql -U bank_diligence -d bank_diligence -c `"SELECT COUNT(*) FROM audit_log;`"" -FailMessage "Database query failed"
        if ($dbCheck.ExitCode -eq 0) {
            $countMatch = $dbCheck.Output -match "(\d+)"
            if ($countMatch) {
                $uatArtifacts.audit_log_count = [int]$matches[1]
                Write-Host "  [OK] Audit log entries: $($uatArtifacts.audit_log_count)" -ForegroundColor Green
            }
        }
    }
} catch {
    Write-Host "  [WARN] Could not query audit log: $_" -ForegroundColor Yellow
}

# ========================================================================
# WRITE UAT ARTIFACT SUMMARY
# ========================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "UAT ARTIFACT SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$uatEndTime = Get-Date
$uatArtifacts.end_time = $uatEndTime.ToString("yyyy-MM-dd HH:mm:ss")
$uatArtifacts.duration_seconds = [math]::Round(($uatEndTime - $uatStartTime).TotalSeconds, 2)

# Write to file
$artifactFile = "scripts\dev\uat_last_run.txt"
$artifactContent = @"
========================================
PILOT UAT RUN - Phase P12
========================================
Start Time: $($uatArtifacts.start_time)
End Time: $($uatArtifacts.end_time)
Duration: $($uatArtifacts.duration_seconds) seconds

URLs:
  Frontend:     http://localhost:3000/dashboard
  API Docs:     http://localhost:8000/docs
  Health Check: http://localhost:8000/api/v1/health/deep

CASE IDs:
  Demo Case: $($uatArtifacts.demo_case_id)
  Demo Doc:  $($uatArtifacts.demo_doc_id)
  Real Case: $($uatArtifacts.real_case_id)
  Real Docs: $($uatArtifacts.real_doc_ids -join ', ')

KPIs:
  Regime: $($uatArtifacts.kpis.regime)
  Risk Label: $($uatArtifacts.kpis.risk_label)
  Readiness: $($uatArtifacts.kpis.readiness_ready)
  Blockers: $($uatArtifacts.kpis.readiness_blockers -join '; ')

EXPORTS:
"@

foreach ($export in $uatArtifacts.exports) {
    $artifactContent += "  - $($export.type): $($export.url)`n"
    $artifactContent += "    Filename: $($export.filename)`n"
    if ($export.expires_at) {
        $artifactContent += "    Expires: $($export.expires_at)`n"
    }
    $artifactContent += "`n"
}

$artifactContent += @"
AUDIT LOG:
  Total Entries: $($uatArtifacts.audit_log_count)

ERRORS:
"@

if ($uatArtifacts.errors.Count -eq 0) {
    $artifactContent += "  None`n"
} else {
    foreach ($error in $uatArtifacts.errors) {
        $artifactContent += "  - $error`n"
    }
}

$artifactContent | Out-File -FilePath $artifactFile -Encoding UTF8
Write-Host "[OK] Artifact summary written to: $artifactFile" -ForegroundColor Green
Write-Host ""

# Print summary
Write-Host $artifactContent

# Final status
if ($uatArtifacts.errors.Count -gt 0) {
    Write-Host ""
    Write-Host "[WARN] UAT completed with errors. Review $artifactFile for details." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host ""
    Write-Host "[OK] UAT completed successfully!" -ForegroundColor Green
    Write-Host ""
    exit 0
}

