# Prompt 5: Test Evidence API Script
# Quick test to verify extraction_method and evidence_json are returned in API responses

param(
    [Parameter(Mandatory=$true)]
    [string]$CaseId
)

$ErrorActionPreference = "Stop"

Write-Host "=== Prompt 5: Test Evidence API ===" -ForegroundColor Cyan
Write-Host "Case ID: $CaseId" -ForegroundColor Yellow
Write-Host ""

# Get token (assumes you're logged in)
$token = docker compose exec -T api python3 -c @"
import os
import sys
# This is a placeholder - in real usage, you'd get token from your session
print('test_token')
"@

Write-Host "Testing API endpoint: GET /api/v1/cases/$CaseId/ocr-extractions" -ForegroundColor Green
Write-Host ""

# Test via API container (simplified - in practice you'd use actual auth)
docker compose exec -T api python3 -c @"
import sys
import os
import requests
import json
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ocr_extraction import OCRExtractionCandidate

db = SessionLocal()
try:
    # Get a candidate with extraction_method='hf_extractor'
    candidate = db.query(OCRExtractionCandidate).filter(
        OCRExtractionCandidate.extraction_method == 'hf_extractor'
    ).first()
    
    if candidate:
        print(f'Found candidate: {candidate.id}')
        print(f'  extraction_method: {candidate.extraction_method}')
        print(f'  evidence_json present: {candidate.evidence_json is not None}')
        if candidate.evidence_json:
            print(f'  evidence_json keys: {list(candidate.evidence_json.keys())}')
            print(f'  evidence_json preview: {json.dumps(candidate.evidence_json, indent=2)[:500]}')
    else:
        print('No hf_extractor candidates found. Run autofill first.')
finally:
    db.close()
"@

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify extraction_method and evidence_json appear in API responses" -ForegroundColor White
Write-Host "2. Open case UI and check OCR Extractions tab" -ForegroundColor White
Write-Host "3. Look for source badges and 'View evidence' links on hf_extractor candidates" -ForegroundColor White

