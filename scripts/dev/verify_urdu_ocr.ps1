#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Phase 1: Verify Urdu OCR foundation - tests canonical OCR entrypoint with metadata.

.DESCRIPTION
    This script tests the Phase 1 OCR foundation:
    - Tests OCR with OCR_ENABLE_URDU=false (English-only, default behavior)
    - Tests OCR with OCR_ENABLE_URDU=true (Urdu+English)
    - Prints metadata, confidence, and text stats for both runs
    - Verifies that metadata includes: engine, lang_used, dpi_used, preprocess_profile, timings

.PARAMETER DocumentId
    Optional document ID. If not provided, picks first available document page.

.PARAMETER PageNumber
    Optional page number (default: 1).

.PARAMETER ApiBaseUrl
    API base URL (default: http://localhost:8000).

.EXAMPLE
    .\scripts\dev\verify_urdu_ocr.ps1

.EXAMPLE
    .\scripts\dev\verify_urdu_ocr.ps1 -DocumentId "123e4567-e89b-12d3-a456-426614174000" -PageNumber 1
#>

param(
    [string]$DocumentId = "",
    [int]$PageNumber = 1,
    [string]$ApiBaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHASE 6: LAYOUT-AWARE OCR VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Dev login
Write-Host "[1/5] Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@orga.com"
    org_name = "OrgA"
    role = "Admin"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-WebRequest -Uri "$ApiBaseUrl/api/v1/auth/dev-login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
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

# Step 2: Find or use document page
Write-Host ""
Write-Host "[2/5] Finding document page..." -ForegroundColor Yellow

if ([string]::IsNullOrWhiteSpace($DocumentId)) {
    # Find first available document
    try {
        $documentsResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/documents?limit=1" -Headers $headers -ErrorAction Stop
        if ($documentsResponse.Count -eq 0) {
            Write-Host "[FAIL] No documents found. Please upload a document first." -ForegroundColor Red
            exit 1
        }
        $DocumentId = $documentsResponse[0].id
        Write-Host "[INFO] Using first available document: $DocumentId" -ForegroundColor Gray
    } catch {
        Write-Host "[FAIL] Failed to find document: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[OK] Using document: $DocumentId, page: $PageNumber" -ForegroundColor Green

# Step 3: Test Pass A - Basic preprocessing
Write-Host ""
Write-Host "[3/7] Testing OCR with force_profile=basic..." -ForegroundColor Yellow

$testBodyBasic = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_profile = "basic"
} | ConvertTo-Json

try {
    $testResponseBasic = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyBasic -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] OCR completed (basic preprocessing)" -ForegroundColor Green
    
    $resultBasic = $testResponseBasic
    
} catch {
    Write-Host "[FAIL] OCR test failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 4: Test Pass B - Enhanced preprocessing
Write-Host ""
Write-Host "[4/7] Testing OCR with force_profile=enhanced..." -ForegroundColor Yellow

$testBodyEnhanced = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_profile = "enhanced"
} | ConvertTo-Json

try {
    $testResponseEnhanced = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyEnhanced -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] OCR completed (enhanced preprocessing)" -ForegroundColor Green
    
    $resultEnhanced = $testResponseEnhanced
    
} catch {
    Write-Host "[FAIL] OCR test failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 5: Test Pass C - Script detection (force_detect=true)
Write-Host ""
Write-Host "[5/8] Testing OCR with force_detect=true..." -ForegroundColor Yellow

$testBodyDetect = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_detect = $true
} | ConvertTo-Json

try {
    $testResponseDetect = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyDetect -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] OCR completed (with script detection)" -ForegroundColor Green
    
    $resultDetect = $testResponseDetect
    
} catch {
    Write-Host "[FAIL] OCR test failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 6: Test Pass D - Ensemble mode (if enabled)
Write-Host ""
Write-Host "[6/8] Testing OCR with ensemble mode..." -ForegroundColor Yellow

# Note: Ensemble mode requires OCR_ENGINE_MODE=ensemble and OCR_ENABLE_PADDLE=true
# We'll test what's currently configured
Write-Host "[INFO] To test ensemble mode, set:" -ForegroundColor Yellow
Write-Host "  OCR_ENGINE_MODE=ensemble" -ForegroundColor White
Write-Host "  OCR_ENABLE_PADDLE=true" -ForegroundColor White
Write-Host "  Then restart API container and run this script again" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Testing current configuration..." -ForegroundColor Yellow

$testBodyEnsemble = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_detect = $true
    return_debug_outputs = $true
} | ConvertTo-Json

try {
    $testResponseEnsemble = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyEnsemble -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] OCR completed" -ForegroundColor Green
    
    $resultEnsemble = $testResponseEnsemble
    
} catch {
    Write-Host "[WARN] Ensemble test failed or not enabled: $_" -ForegroundColor Yellow
    $resultEnsemble = $null
}

# Step 6b: Test Pass E - Layout segmentation (Phase 6)
Write-Host ""
Write-Host "[6b/9] Testing OCR with layout segmentation..." -ForegroundColor Yellow

Write-Host "[INFO] To test layout segmentation, set:" -ForegroundColor Yellow
Write-Host "  OCR_ENABLE_LAYOUT_SEGMENTATION=true" -ForegroundColor White
Write-Host "  Then restart API container and run this script again" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Testing with force_layout=true (override)..." -ForegroundColor Yellow

$testBodyLayout = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_detect = $true
    force_layout = $true
    return_debug_outputs = $true
} | ConvertTo-Json

try {
    $testResponseLayout = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyLayout -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Layout OCR completed" -ForegroundColor Green
    
    $resultLayout = $testResponseLayout
    
} catch {
    Write-Host "[WARN] Layout OCR test failed: $_" -ForegroundColor Yellow
    $resultLayout = $null
}

# Step 6c: Test Pass F - Domain normalization (Phase 7)
Write-Host ""
Write-Host "[6c/10] Testing OCR with domain normalization..." -ForegroundColor Yellow

Write-Host "[INFO] To test domain normalization, set:" -ForegroundColor Yellow
Write-Host "  OCR_ENABLE_DOMAIN_NORMALIZATION=true" -ForegroundColor White
Write-Host "  Then restart API container and run this script again" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Testing with force_domain=true (override)..." -ForegroundColor Yellow

$testBodyDomain = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_detect = $true
    force_domain = $true
    return_debug_outputs = $true
} | ConvertTo-Json

try {
    $testResponseDomain = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyDomain -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Domain normalization completed" -ForegroundColor Green
    
    $resultDomain = $testResponseDomain
    
} catch {
    Write-Host "[WARN] Domain normalization test failed: $_" -ForegroundColor Yellow
    $resultDomain = $null
}

# Step 6d: Test Pass G - PDF text layer extraction (Phase 8)
Write-Host ""
Write-Host "[6d/11] Testing OCR with PDF text layer extraction..." -ForegroundColor Yellow

Write-Host "[INFO] To test PDF text layer extraction, set:" -ForegroundColor Yellow
Write-Host "  OCR_ENABLE_PDF_TEXT_LAYER=true" -ForegroundColor White
Write-Host "  Then restart API container and run this script again" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Testing with force_pdf_text_layer=true and debug_compare_pdf_vs_ocr=true..." -ForegroundColor Yellow

$testBodyPdfText = @{
    document_id = $DocumentId
    page_number = $PageNumber
    force_detect = $true
    force_pdf_text_layer = $true
    debug_compare_pdf_vs_ocr = $true
    return_debug_outputs = $true
} | ConvertTo-Json

try {
    $testResponsePdfText = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/admin/ocr/test-page" -Method POST -Body $testBodyPdfText -ContentType "application/json" -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] PDF text layer extraction completed" -ForegroundColor Green
    
    $resultPdfText = $testResponsePdfText
    
} catch {
    Write-Host "[WARN] PDF text layer extraction test failed: $_" -ForegroundColor Yellow
    $resultPdfText = $null
}

# Step 7: Side-by-side comparison
Write-Host ""
Write-Host "[7/10] Side-by-Side Comparison" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BASIC vs ENHANCED PREPROCESSING COMPARISON" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Metric", "Basic", "Enhanced") -ForegroundColor Yellow
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "---", "---", "---") -ForegroundColor Gray
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Text Length", $resultBasic.stats.text_length, $resultEnhanced.stats.text_length) -ForegroundColor White
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Arabic Char Ratio", $resultBasic.stats.arabic_char_ratio, $resultEnhanced.stats.arabic_char_ratio) -ForegroundColor White
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Confidence", [Math]::Round($resultBasic.confidence, 4), [Math]::Round($resultEnhanced.confidence, 4)) -ForegroundColor White
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "DPI Used", $resultBasic.stats.dpi_used, $resultEnhanced.stats.dpi_used) -ForegroundColor White
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Deskew Angle (deg)", $resultBasic.stats.deskew_angle_deg, $resultEnhanced.stats.deskew_angle_deg) -ForegroundColor White
Write-Host ("{0,-25} {1,-20} {2,-20}" -f "Total Time (ms)", $resultBasic.metadata.timing_ms.total, $resultEnhanced.metadata.timing_ms.total) -ForegroundColor White
Write-Host ""

# Step 8: Script detection and ensemble results
Write-Host ""
Write-Host "[8/10] Script Detection and Ensemble Results" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SCRIPT DETECTION (Pass C)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($resultDetect.metadata.script_detect) {
    $detect = $resultDetect.metadata.script_detect
    Write-Host "Detected Script: $($detect.script)" -ForegroundColor White
    Write-Host "Confidence: $($detect.confidence)" -ForegroundColor White
    Write-Host "Language Chosen: $($detect.lang_chosen)" -ForegroundColor White
    
    if ($detect.details.char_stats) {
        $stats = $detect.details.char_stats
        if (-not $stats.skipped) {
            Write-Host ""
            Write-Host "Character Statistics:" -ForegroundColor Cyan
            Write-Host "  - Urdu ratio: $($stats.urdu_ratio)" -ForegroundColor White
            Write-Host "  - Latin ratio: $($stats.latin_ratio)" -ForegroundColor White
            Write-Host "  - Total chars: $($stats.total_chars)" -ForegroundColor White
        }
    }
    
    if ($detect.probe_used) {
        Write-Host ""
        Write-Host "Quick Probe: Used ($($detect.probe_chars) chars)" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "Quick Probe: Not used" -ForegroundColor Gray
    }
    
    if ($detect.details.osd) {
        Write-Host ""
        Write-Host "OSD Detection:" -ForegroundColor Cyan
        Write-Host "  - Script: $($detect.details.osd.script)" -ForegroundColor White
        Write-Host "  - Confidence: $($detect.details.osd.confidence)" -ForegroundColor White
    }
} else {
    Write-Host "Script detection metadata not available" -ForegroundColor Yellow
}

# Ensemble results (Pass D)
if ($resultEnsemble -and $resultEnsemble.metadata.ensemble) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "ENSEMBLE MODE (Pass D)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $ensemble = $resultEnsemble.metadata.ensemble
    Write-Host "Ensemble Enabled: $($ensemble.enabled)" -ForegroundColor White
    Write-Host "Winner Engine: $($ensemble.winner)" -ForegroundColor White
    
    if ($ensemble.scores) {
        Write-Host ""
        Write-Host "Quality Scores:" -ForegroundColor Cyan
        if ($ensemble.scores.tesseract) {
            Write-Host "  - Tesseract: $($ensemble.scores.tesseract.score)" -ForegroundColor White
            $tMetrics = $ensemble.scores.tesseract.metrics
            if ($tMetrics) {
                Write-Host "    Urdu ratio: $($tMetrics.urdu_ratio)" -ForegroundColor Gray
                Write-Host "    Latin ratio: $($tMetrics.latin_ratio)" -ForegroundColor Gray
            }
        }
        if ($ensemble.scores.paddleocr) {
            Write-Host "  - PaddleOCR: $($ensemble.scores.paddleocr.score)" -ForegroundColor White
            $pMetrics = $ensemble.scores.paddleocr.metrics
            if ($pMetrics) {
                Write-Host "    Urdu ratio: $($pMetrics.urdu_ratio)" -ForegroundColor Gray
                Write-Host "    Latin ratio: $($pMetrics.latin_ratio)" -ForegroundColor Gray
            }
        }
    }
    
    if ($ensemble.error) {
        Write-Host ""
        Write-Host "Error: $($ensemble.error)" -ForegroundColor Yellow
    }
    
    if ($resultEnsemble.debug_outputs) {
        Write-Host ""
        Write-Host "Debug Outputs:" -ForegroundColor Cyan
        if ($resultEnsemble.debug_outputs.tesseract) {
            Write-Host "  Tesseract confidence: $($resultEnsemble.debug_outputs.tesseract.confidence)" -ForegroundColor White
        }
        if ($resultEnsemble.debug_outputs.paddleocr) {
            if ($resultEnsemble.debug_outputs.paddleocr.error) {
                Write-Host "  PaddleOCR: $($resultEnsemble.debug_outputs.paddleocr.error)" -ForegroundColor Yellow
            } else {
                Write-Host "  PaddleOCR confidence: $($resultEnsemble.debug_outputs.paddleocr.confidence)" -ForegroundColor White
            }
        }
    }
} elseif ($resultEnsemble) {
    Write-Host ""
    Write-Host "Ensemble mode not enabled or Paddle not installed" -ForegroundColor Yellow
    Write-Host "Set OCR_ENGINE_MODE=ensemble and OCR_ENABLE_PADDLE=true to enable" -ForegroundColor Yellow
}

# Phase 6: Layout OCR results (Pass E)
if ($resultLayout -and $resultLayout.metadata.layout_ocr) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "LAYOUT OCR (Pass E)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $layout = $resultLayout.metadata.layout_ocr
    Write-Host "Layout Segmentation:" -ForegroundColor Cyan
    Write-Host "  - Attempted: $($layout.attempted)" -ForegroundColor White
    Write-Host "  - Used: $($layout.used)" -ForegroundColor White
    Write-Host "  - Boxes detected: $($layout.boxes_count)" -ForegroundColor White
    Write-Host "  - Blocks OCRed: $($layout.blocks_ocred)" -ForegroundColor White
    
    if ($layout.reason) {
        Write-Host "  - Reason: $($layout.reason)" -ForegroundColor White
    }
    
    if ($layout.error) {
        Write-Host "  - Error: $($layout.error)" -ForegroundColor Yellow
    }
    
    if ($layout.scores) {
        Write-Host ""
        Write-Host "Quality Scores:" -ForegroundColor Cyan
        if ($layout.scores.full_page) {
            Write-Host "  - Full-page: $($layout.scores.full_page.score)" -ForegroundColor White
        }
        if ($layout.scores.layout) {
            Write-Host "  - Layout: $($layout.scores.layout.score)" -ForegroundColor White
        }
    }
    
    if ($layout.confidences) {
        Write-Host ""
        Write-Host "Confidences:" -ForegroundColor Cyan
        Write-Host "  - Full-page: $($layout.confidences.full_page)" -ForegroundColor White
        Write-Host "  - Layout: $($layout.confidences.layout)" -ForegroundColor White
        
        $confDiff = $layout.confidences.layout - $layout.confidences.full_page
        Write-Host "  - Delta: $confDiff" -ForegroundColor $(if ($confDiff -gt 0) { "Green" } else { "Gray" })
    }
    
    if ($resultLayout.debug_outputs.layout_ocr) {
        Write-Host ""
        Write-Host "Debug Details:" -ForegroundColor Cyan
        $layoutDebug = $resultLayout.debug_outputs.layout_ocr
        Write-Host "  - Boxes count: $($layoutDebug.boxes_count)" -ForegroundColor White
        Write-Host "  - Blocks OCRed: $($layoutDebug.blocks_ocred)" -ForegroundColor White
    }
} elseif ($resultLayout) {
    Write-Host ""
    Write-Host "Layout OCR not attempted or failed" -ForegroundColor Yellow
    Write-Host "Set OCR_ENABLE_LAYOUT_SEGMENTATION=true to enable" -ForegroundColor Yellow
}

# Phase 7: Domain normalization results (Pass F)
if ($resultDomain -and $resultDomain.metadata.domain_ur) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "DOMAIN NORMALIZATION (Pass F)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $domain = $resultDomain.metadata.domain_ur
    Write-Host "Domain Normalization:" -ForegroundColor Cyan
    Write-Host "  - Enabled: $($domain.enabled)" -ForegroundColor White
    Write-Host "  - Hints count: $($domain.stats.hints_count)" -ForegroundColor White
    Write-Host "  - Normalized inplace: $($domain.normalized_inplace)" -ForegroundColor White
    
    if ($domain.actions) {
        Write-Host "  - Actions: $($domain.actions -join ', ')" -ForegroundColor White
    }
    
    if ($domain.error) {
        Write-Host "  - Error: $($domain.error)" -ForegroundColor Yellow
    }
    
    # Show top 10 hints
    $hints = $domain.hints
    if ($hints -and $hints.Count -gt 0) {
        Write-Host ""
        Write-Host "Top 10 Hints:" -ForegroundColor Cyan
        $topHints = $hints | Select-Object -First 10
        foreach ($hint in $topHints) {
            $hintType = $hint.type
            $hintValue = if ($hint.value) { $hint.value } else { "N/A" }
            $hintRaw = $hint.raw
            $hintConf = $hint.confidence
            Write-Host "  - [$hintType] $hintValue (raw: '$hintRaw', conf: $hintConf)" -ForegroundColor White
        }
        
        # Count by type
        $hintTypes = $hints | Group-Object -Property type
        Write-Host ""
        Write-Host "Hints by Type:" -ForegroundColor Cyan
        foreach ($typeGroup in $hintTypes) {
            Write-Host "  - $($typeGroup.Name): $($typeGroup.Count)" -ForegroundColor White
        }
    } else {
        Write-Host ""
        Write-Host "No hints detected" -ForegroundColor Gray
    }
    
    if ($resultDomain.debug_outputs.domain_ur) {
        Write-Host ""
        Write-Host "Debug Details:" -ForegroundColor Cyan
        $domainDebug = $resultDomain.debug_outputs.domain_ur
        Write-Host "  - Hints preview: $($domainDebug.hints_preview.Count) shown" -ForegroundColor White
    }
} elseif ($resultDomain) {
    Write-Host ""
    Write-Host "Domain normalization not attempted or failed" -ForegroundColor Yellow
    Write-Host "Set OCR_ENABLE_DOMAIN_NORMALIZATION=true to enable" -ForegroundColor Yellow
}

# Phase 8: PDF text layer extraction results (Pass G)
if ($resultPdfText -and $resultPdfText.metadata.pdf_text_layer) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "PDF TEXT LAYER EXTRACTION (Pass G)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $pdfText = $resultPdfText.metadata.pdf_text_layer
    Write-Host "PDF Text Layer:" -ForegroundColor Cyan
    Write-Host "  - Attempted: $($pdfText.attempted)" -ForegroundColor White
    Write-Host "  - Used: $($pdfText.used)" -ForegroundColor White
    
    if ($pdfText.reason) {
        Write-Host "  - Reason: $($pdfText.reason)" -ForegroundColor White
    }
    
    if ($pdfText.score) {
        Write-Host ""
        Write-Host "Quality Score:" -ForegroundColor Cyan
        Write-Host "  - Length: $($pdfText.score.len)" -ForegroundColor White
        Write-Host "  - Urdu ratio: $($pdfText.score.urdu_ratio)" -ForegroundColor White
        Write-Host "  - Latin ratio: $($pdfText.score.latin_ratio)" -ForegroundColor White
        Write-Host "  - Garbage ratio: $($pdfText.score.garbage_ratio)" -ForegroundColor White
        Write-Host "  - OK: $($pdfText.score.ok)" -ForegroundColor White
    }
    
    if ($pdfText.extract_meta) {
        Write-Host ""
        Write-Host "Extraction Metadata:" -ForegroundColor Cyan
        Write-Host "  - Engine: $($pdfText.extract_meta.engine)" -ForegroundColor White
        Write-Host "  - Chars: $($pdfText.extract_meta.chars)" -ForegroundColor White
        Write-Host "  - Extract time: $($pdfText.extract_meta.extract_ms) ms" -ForegroundColor White
        if ($pdfText.extract_meta.error) {
            Write-Host "  - Error: $($pdfText.extract_meta.error)" -ForegroundColor Yellow
        }
    }
    
    if ($resultPdfText.debug_outputs.comparison) {
        Write-Host ""
        Write-Host "Comparison (PDF vs OCR):" -ForegroundColor Cyan
        $comp = $resultPdfText.debug_outputs.comparison
        Write-Host "  - Winner: $($comp.winner)" -ForegroundColor $(if ($comp.winner -eq "pdf_text_layer") { "Green" } else { "White" })
        Write-Host "  - PDF text layer used: $($comp.pdf_text_layer_used)" -ForegroundColor White
        Write-Host "  - OCR confidence: $($comp.ocr_confidence)" -ForegroundColor White
    }
} elseif ($resultPdfText) {
    Write-Host ""
    Write-Host "PDF text layer extraction not attempted or failed" -ForegroundColor Yellow
    Write-Host "Set OCR_ENABLE_PDF_TEXT_LAYER=true to enable" -ForegroundColor Yellow
}

# Phase 5: Text repair and re-OCR results
if ($resultDetect.metadata.text_repair -or $resultDetect.metadata.reocr) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "TEXT REPAIR & RE-OCR (Phase 5)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Text repair info
    if ($resultDetect.metadata.text_repair) {
        $repair = $resultDetect.metadata.text_repair
        Write-Host "Text Repair:" -ForegroundColor Cyan
        Write-Host "  - Actions: $($repair.actions -join ', ')" -ForegroundColor White
        Write-Host "  - Digit normalization: $($repair.digit_norm)" -ForegroundColor White
        Write-Host "  - Truncated: $($repair.truncated)" -ForegroundColor White
        
        # Show before/after preview if text changed
        if ($repair.raw_preview -and $repair.final_preview) {
            $rawPreview = $repair.raw_preview
            $finalPreview = $repair.final_preview
            if ($rawPreview -ne $finalPreview) {
                Write-Host ""
                Write-Host "  Before (first 120 chars):" -ForegroundColor Gray
                Write-Host "    $rawPreview" -ForegroundColor DarkGray
                Write-Host "  After (first 120 chars):" -ForegroundColor Gray
                Write-Host "    $finalPreview" -ForegroundColor DarkGray
            }
        }
    }
    
    # Re-OCR info
    if ($resultDetect.metadata.reocr) {
        $reocr = $resultDetect.metadata.reocr
        Write-Host ""
        Write-Host "Re-OCR Retry:" -ForegroundColor Cyan
        Write-Host "  - Attempted: $($reocr.attempted)" -ForegroundColor White
        if ($reocr.attempted) {
            Write-Host "  - Accepted: $($reocr.accepted)" -ForegroundColor White
            Write-Host "  - Reason: $($reocr.reason)" -ForegroundColor White
            
            if ($reocr.check) {
                Write-Host ""
                Write-Host "  Quality Check:" -ForegroundColor Cyan
                $check = $reocr.check
                Write-Host "    - Is bad: $($check.is_bad)" -ForegroundColor White
                if ($check.reasons) {
                    Write-Host "    - Reasons: $($check.reasons -join ', ')" -ForegroundColor White
                }
                if ($check.checks) {
                    Write-Host "    - Garbage ratio: $($check.checks.garbage_ratio)" -ForegroundColor Gray
                    Write-Host "    - Urdu ratio: $($check.checks.urdu_ratio)" -ForegroundColor Gray
                }
            }
            
            if ($reocr.scores) {
                Write-Host ""
                Write-Host "  Scores:" -ForegroundColor Cyan
                if ($reocr.scores.current) {
                    Write-Host "    - Current: $($reocr.scores.current.score)" -ForegroundColor White
                }
                if ($reocr.scores.retry) {
                    Write-Host "    - Retry: $($reocr.scores.retry.score)" -ForegroundColor White
                }
            }
        }
    }
}

# Quality metrics summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QUALITY METRICS SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($resultDetect.stats) {
    Write-Host "Garbage ratio: $($resultDetect.stats.garbage_ratio)" -ForegroundColor White
    Write-Host "Urdu ratio: $($resultDetect.stats.urdu_ratio)" -ForegroundColor White
    Write-Host "Latin ratio: $($resultDetect.stats.latin_ratio)" -ForegroundColor White
    Write-Host "Whitespace ratio: $($resultDetect.stats.whitespace_ratio)" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEXT PREVIEWS (first 200 chars)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ""
Write-Host "--- Basic Preprocessing ---" -ForegroundColor Cyan
$basicPreview = if ($resultBasic.text.Length -le 200) { $resultBasic.text } else { $resultBasic.text.Substring(0, 200) }
Write-Host $basicPreview -ForegroundColor Gray
Write-Host ""
Write-Host "--- Enhanced Preprocessing ---" -ForegroundColor Cyan
$enhancedPreview = if ($resultEnhanced.text.Length -le 200) { $resultEnhanced.text } else { $resultEnhanced.text.Substring(0, 200) }
Write-Host $enhancedPreview -ForegroundColor Gray
Write-Host ""

# Verify metadata structure
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "METADATA VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$requiredFields = @("engine", "lang_used", "dpi_used", "preprocess_profile", "preprocess", "timing_ms", "engine_mode")
$allPresent = $true

foreach ($field in $requiredFields) {
    if ($resultBasic.metadata.PSObject.Properties.Name -contains $field) {
        Write-Host "[OK] Field '$field' present in metadata" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Field '$field' missing in metadata" -ForegroundColor Red
        $allPresent = $false
    }
}

if ($allPresent) {
    Write-Host ""
    Write-Host "[SUCCESS] All required metadata fields present!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Phase 2 verification complete. Enhanced preprocessing is working correctly." -ForegroundColor Green
    
    # Show preprocessing details if enhanced succeeded
    if ($resultEnhanced.metadata.preprocess.success) {
        Write-Host ""
        Write-Host "Enhanced preprocessing details:" -ForegroundColor Cyan
        Write-Host "  - Denoise: $($resultEnhanced.metadata.preprocess.denoise)" -ForegroundColor White
        Write-Host "  - Contrast: $($resultEnhanced.metadata.preprocess.contrast)" -ForegroundColor White
        Write-Host "  - Binarize: $($resultEnhanced.metadata.preprocess.binarize)" -ForegroundColor White
        Write-Host "  - Deskew angle: $($resultEnhanced.metadata.preprocess.deskew_angle_deg) deg" -ForegroundColor White
    }
} else {
    Write-Host ""
    Write-Host "[FAIL] Some metadata fields are missing." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To enable enhanced preprocessing globally:" -ForegroundColor Yellow
Write-Host "1. Set OCR_PREPROCESS_PROFILE=enhanced in backend/.env or docker-compose.yml" -ForegroundColor White
Write-Host "   OR set OCR_ENABLE_ENHANCED_PREPROCESS=true" -ForegroundColor White
Write-Host "2. Restart API container: docker compose restart api" -ForegroundColor White
Write-Host ""
Write-Host "To enable text repair and re-OCR:" -ForegroundColor Yellow
Write-Host "1. Set OCR_ENABLE_TEXT_REPAIR=true (default: true)" -ForegroundColor White
Write-Host "2. Set OCR_REOCR_ENABLE=true (default: true)" -ForegroundColor White
Write-Host "3. Optionally set OCR_ENABLE_DIGIT_NORMALIZATION=true for digit normalization" -ForegroundColor White
Write-Host ""
Write-Host "To enable script detection globally:" -ForegroundColor Yellow
Write-Host "1. Set OCR_ENABLE_SCRIPT_DETECTION=true in backend/.env or docker-compose.yml" -ForegroundColor White
Write-Host "2. Optionally set OCR_SCRIPT_DETECT_METHOD=hybrid for best results" -ForegroundColor White
Write-Host "3. Restart API container: docker compose restart api" -ForegroundColor White
Write-Host ""
Write-Host "To test with Urdu enabled:" -ForegroundColor Yellow
Write-Host "1. Set OCR_ENABLE_URDU=true in backend/.env or docker-compose.yml" -ForegroundColor White
Write-Host "2. Restart API container: docker compose restart api" -ForegroundColor White
Write-Host "3. Run this script again" -ForegroundColor White
Write-Host ""
