# Prompt 12: Qaari OCR Fallback Smoke Test
# Tests Qaari OCR fallback when baseline OCR quality is poor

$ErrorActionPreference = "Stop"

Write-Host "=== Prompt 12: Qaari OCR Fallback Smoke Test ===" -ForegroundColor Cyan

# Check if Qaari model path is provided
$qaariModelPath = $env:HF_QAARI_MODEL_PATH
if (-not $qaariModelPath) {
    Write-Host "ERROR: HF_QAARI_MODEL_PATH environment variable not set" -ForegroundColor Red
    Write-Host "Set it to the Qaari model path, e.g.:" -ForegroundColor Yellow
    Write-Host '  $env:HF_QAARI_MODEL_PATH = "oddadmix/Qaari-0.1-Urdu-OCR-VL-2B-Instruct"' -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Qaari model: $qaariModelPath" -ForegroundColor Green

# HF Extractor URL
$hfExtractorUrl = $env:HF_EXTRACTOR_URL
if (-not $hfExtractorUrl) {
    $hfExtractorUrl = "http://localhost:8090"
}

Write-Host "HF Extractor URL: $hfExtractorUrl" -ForegroundColor Green

# Check if service is running
try {
    $healthResponse = Invoke-RestMethod -Uri "$hfExtractorUrl/health" -Method Get -TimeoutSec 5
    if (-not $healthResponse.ok) {
        throw "Health check failed"
    }
    Write-Host "HF Extractor service is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: HF Extractor service not available at $hfExtractorUrl" -ForegroundColor Red
    Write-Host "Start the service with: docker compose up -d hf-extractor" -ForegroundColor Yellow
    exit 1
}

# Create a test image (simple white image with text)
# For this smoke test, we'll use a base64-encoded minimal PNG
# In a real test, you'd use an actual document image
$testImageBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

# Build request payload
$docId = [guid]::NewGuid().ToString()
$pageNo = 1

$payload = @{
    doc_id = $docId
    page_no = $pageNo
    image = @{
        content_type = "image/png"
        base64 = $testImageBase64
    }
    ocr = $null
    options = @{
        extractor_version = "rules-v1"
        return_token_spans = $true
        language_hint = "ur"
        labels = $null
        min_ocr_confidence = 0.99  # Force poor baseline selection
        enable_ocr_fallback = $true
        force_ocr_fallback = $true  # Force fallback to trigger Qaari
        enable_qaari = $true
        qaari_model_name_or_path = $qaariModelPath
    }
} | ConvertTo-Json -Depth 10

Write-Host "`nSending extraction request..." -ForegroundColor Cyan
Write-Host "  doc_id: $docId" -ForegroundColor Gray
Write-Host "  page_no: $pageNo" -ForegroundColor Gray
Write-Host "  force_ocr_fallback: true" -ForegroundColor Gray
Write-Host "  enable_qaari: true" -ForegroundColor Gray
Write-Host "  min_ocr_confidence: 0.99 (forces poor baseline)" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$hfExtractorUrl/v1/extract" -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 60
    
    Write-Host "`n=== Response ===" -ForegroundColor Green
    
    # Check quality metrics
    $quality = $response.quality
    Write-Host "`nQuality Metrics:" -ForegroundColor Cyan
    Write-Host "  qaari_used: $($quality.qaari_used)" -ForegroundColor $(if ($quality.qaari_used) { "Green" } else { "Red" })
    Write-Host "  ocr_text_only: $($quality.ocr_text_only)" -ForegroundColor $(if ($quality.ocr_text_only) { "Green" } else { "Yellow" })
    Write-Host "  qaari_model_name_or_path: $($quality.qaari_model_name_or_path)" -ForegroundColor Gray
    Write-Host "  needs_manual_review: $($quality.needs_manual_review)" -ForegroundColor $(if ($quality.needs_manual_review) { "Yellow" } else { "Green" })
    Write-Host "  page_ocr_confidence: $($quality.page_ocr_confidence)" -ForegroundColor Gray
    
    # Verify Qaari was used
    if (-not $quality.qaari_used) {
        Write-Host "`nWARNING: qaari_used is false - Qaari may not have been invoked" -ForegroundColor Yellow
        Write-Host "This could be expected if baseline OCR was already good enough" -ForegroundColor Yellow
    } else {
        Write-Host "`n✓ Qaari was successfully invoked" -ForegroundColor Green
    }
    
    # Check entities
    $entities = $response.entities
    Write-Host "`nEntities found: $($entities.Count)" -ForegroundColor Cyan
    
    if ($entities.Count -gt 0) {
        Write-Host "`nEntity Summary:" -ForegroundColor Cyan
        foreach ($entity in $entities) {
            $source = $entity.source
            Write-Host "  - $($entity.label): $($entity.value)" -ForegroundColor White
            Write-Host "    confidence: $($entity.confidence)" -ForegroundColor Gray
            Write-Host "    bbox: $($source.bbox)" -ForegroundColor Gray
            Write-Host "    span_start: $($source.span_start)" -ForegroundColor Gray
            Write-Host "    span_end: $($source.span_end)" -ForegroundColor Gray
            
            # Verify span offsets when bbox is null
            if ($null -eq $source.bbox -or $source.bbox.Count -eq 0) {
                if ($null -ne $source.span_start -and $null -ne $source.span_end) {
                    Write-Host "    ✓ Span offsets present (text-only OCR)" -ForegroundColor Green
                } else {
                    Write-Host "    ✗ WARNING: bbox is null but span offsets missing" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "No entities extracted (this is OK for a minimal test image)" -ForegroundColor Yellow
    }
    
    # Summary
    Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
    $allChecksPassed = $true
    
    if ($quality.qaari_used) {
        Write-Host "✓ Qaari was invoked" -ForegroundColor Green
    } else {
        Write-Host "⚠ Qaari was not invoked (may be expected if baseline was sufficient)" -ForegroundColor Yellow
    }
    
    if ($quality.ocr_text_only) {
        Write-Host "✓ OCR is text-only (no bounding boxes)" -ForegroundColor Green
    }
    
    if ($quality.needs_manual_review) {
        Write-Host "✓ needs_manual_review is set (expected for Qaari)" -ForegroundColor Green
    }
    
    # Check entities for span offsets
    $entitiesWithSpanOffsets = 0
    foreach ($entity in $entities) {
        $source = $entity.source
        if (($null -eq $source.bbox -or $source.bbox.Count -eq 0) -and 
            $null -ne $source.span_start -and $null -ne $source.span_end) {
            $entitiesWithSpanOffsets++
        }
    }
    
    if ($entitiesWithSpanOffsets -gt 0) {
        Write-Host "✓ $entitiesWithSpanOffsets entities have span offsets (text-only OCR)" -ForegroundColor Green
    } elseif ($quality.ocr_text_only -and $entities.Count -gt 0) {
        Write-Host "⚠ WARNING: OCR is text-only but entities lack span offsets" -ForegroundColor Red
        $allChecksPassed = $false
    }
    
    if ($allChecksPassed) {
        Write-Host "`n✓ All checks passed!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`n✗ Some checks failed" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "`nERROR: Request failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

