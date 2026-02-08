# Prompt 6: Candidate Gate Smoke Test
# Tests that the candidate gate normalizes and validates candidates correctly

param(
    [Parameter(Mandatory=$true)]
    [string]$CaseId
)

$ErrorActionPreference = "Stop"

Write-Host "=== Prompt 6: Candidate Gate Smoke Test ===" -ForegroundColor Cyan
Write-Host "Case ID: $CaseId" -ForegroundColor Yellow
Write-Host ""

# Test 1: Check candidates by extraction_method and field_key
Write-Host "[1/3] Checking candidates by extraction_method and field_key..." -ForegroundColor Green
Write-Host ""

$query1 = @"
SELECT 
    extraction_method,
    field_key,
    COUNT(*) as candidate_count
FROM ocr_extraction_candidates
WHERE case_id = '$CaseId'
GROUP BY extraction_method, field_key
ORDER BY extraction_method, field_key;
"@

docker compose exec -T db psql -U bank_diligence -d bank_diligence -c $query1

Write-Host ""

# Test 2: Show top 30 newest candidates with normalized_value in evidence_json
Write-Host "[2/3] Showing top 30 newest candidates with evidence_json normalized_value..." -ForegroundColor Green
Write-Host ""

$query2 = @"
SELECT 
    field_key,
    extraction_method,
    proposed_value,
    evidence_json->>'normalized_value' as normalized_value,
    evidence_json->>'raw_value' as raw_value,
    page_number,
    created_at
FROM ocr_extraction_candidates
WHERE case_id = '$CaseId'
  AND evidence_json IS NOT NULL
ORDER BY created_at DESC
LIMIT 30;
"@

docker compose exec -T db psql -U bank_diligence -d bank_diligence -c $query2

Write-Host ""

# Test 3: Verify CNIC normalization (should be hyphenated)
Write-Host "[3/3] Verifying CNIC normalization (should be hyphenated format)..." -ForegroundColor Green
Write-Host ""

$query3 = @"
SELECT 
    field_key,
    extraction_method,
    proposed_value,
    CASE 
        WHEN proposed_value ~ '^\d{5}-\d{7}-\d{1}$' THEN 'PASS (hyphenated)'
        WHEN proposed_value ~ '^\d{13}$' THEN 'FAIL (not normalized)'
        ELSE 'CHECK (unexpected format)'
    END as normalization_status,
    evidence_json->>'raw_value' as raw_value,
    evidence_json->>'normalized_value' as normalized_value
FROM ocr_extraction_candidates
WHERE case_id = '$CaseId'
  AND field_key = 'party.cnic'
ORDER BY created_at DESC
LIMIT 20;
"@

$cnics = docker compose exec -T db psql -U bank_diligence -d bank_diligence -c $query3
Write-Host $cnics

Write-Host ""

# Test 4: Verify plot number length (should be <= 12 chars)
Write-Host "[4/3] Verifying plot number length (should be <= 12 chars)..." -ForegroundColor Green
Write-Host ""

$query4 = @"
SELECT 
    field_key,
    extraction_method,
    proposed_value,
    LENGTH(proposed_value) as value_length,
    CASE 
        WHEN LENGTH(proposed_value) <= 12 THEN 'PASS'
        ELSE 'FAIL (too long)'
    END as length_status,
    evidence_json->>'raw_value' as raw_value
FROM ocr_extraction_candidates
WHERE case_id = '$CaseId'
  AND field_key = 'property.plot_number'
ORDER BY created_at DESC
LIMIT 20;
"@

$plots = docker compose exec -T db psql -U bank_diligence -d bank_diligence -c $query4
Write-Host $plots

Write-Host ""

# Summary
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "PASS criteria:" -ForegroundColor Yellow
Write-Host "  ✓ At least one hf_extractor CNIC candidate exists" -ForegroundColor White
Write-Host "  ✓ All CNIC candidates are in hyphenated format (XXXXX-XXXXXXX-X)" -ForegroundColor White
Write-Host "  ✓ Plot number candidates (if any) have <= 12 chars" -ForegroundColor White
Write-Host "  ✓ Evidence JSON includes raw_value and normalized_value" -ForegroundColor White
Write-Host ""
Write-Host "Check the queries above to verify these criteria." -ForegroundColor White

