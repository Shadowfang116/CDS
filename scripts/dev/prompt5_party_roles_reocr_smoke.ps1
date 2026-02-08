#!/usr/bin/env pwsh
# Prompt 5 Party Roles Re-OCR Smoke Test
# Tests OCR fallback and party role extraction directly

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$SALE_DEED_DOC_ID = "8fa48b2d-c169-450e-8b16-8855b6a83def"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 5 PARTY ROLES RE-OCR SMOKE TEST" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/2] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "[OK] Docker engine is reachable" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Docker engine is not reachable. Please ensure Docker Desktop is running." -ForegroundColor Red
    exit 1
}

# Run smoke test inside API container
Write-Host ""
Write-Host "[2/2] Running smoke test..." -ForegroundColor Yellow

$docIdStr = "8fa48b2d-c169-450e-8b16-8855b6a83def"
$pythonScript = @"
import uuid
import sys
from app.db.session import SessionLocal
from app.services.ocr_fallback import get_page_text_with_fallback
from app.services.extractors.party_roles import extract_party_roles_from_document, PageOCR
from app.services.ocr_text_quality import is_arabic_char, detect_mojibake

# Use default org_id (from dev setup)
org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
doc_id = uuid.UUID("$docIdStr")

db = SessionLocal()
try:
    # Get all pages for the document
    from app.models.document import DocumentPage
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc_id,
        DocumentPage.org_id == org_id,
    ).order_by(DocumentPage.page_number).all()
    
    print("=" * 60)
    print("PAGE-BY-PAGE OCR FALLBACK TEST")
    print("=" * 60)
    
    doc_pages_ocr = []
    for page in pages:
        page_num = page.page_number
        original_text = page.ocr_text or ""
        
        # Check original text stats
        _, mojibake_ratio_before, _, _ = detect_mojibake(original_text)
        arabic_count_before = sum(1 for c in original_text if is_arabic_char(c))
        corrupted_before = mojibake_ratio_before > 0.02
        
        # Get text with fallback
        corrected_text = get_page_text_with_fallback(
            db=db,
            org_id=org_id,
            document_id=doc_id,
            page_number=page_num,
            use_corrections=True,
        )
        
        # Check corrected text stats
        _, mojibake_ratio_after, _, _ = detect_mojibake(corrected_text)
        arabic_count_after = sum(1 for c in corrected_text if is_arabic_char(c))
        
        # Determine OCR source (check if text changed)
        ocr_source_after = "tesseract_fallback" if corrected_text != original_text else "original"
        
        print(f"Page {page_num}:")
        print(f"  corrupted_before={corrupted_before} mojibake_ratio_before={mojibake_ratio_before:.3f}")
        print(f"  ocr_source_after={ocr_source_after}")
        print(f"  arabic_char_count_after={arabic_count_after} mojibake_ratio_after={mojibake_ratio_after:.3f}")
        print(f"  text_length={len(corrected_text)}")
        print("")
        
        # Build PageOCR for extraction
        doc_pages_ocr.append(PageOCR(
            document_id=str(doc_id),
            document_name="sale_deed.pdf",
            page_number=page_num,
            text=corrected_text
        ))
    
    print("=" * 60)
    print("PARTY ROLE EXTRACTION TEST")
    print("=" * 60)
    
    # Extract party roles
    roles = extract_party_roles_from_document(doc_pages_ocr)
    
    print(f"seller: \"{roles.get('seller_names', '')}\" method={roles.get('evidence', {}).get('role_method', {}).get('seller', 'unknown')}")
    print(f"buyer: \"{roles.get('buyer_names', '')}\" method={roles.get('evidence', {}).get('role_method', {}).get('buyer', 'unknown')}")
    print(f"witness: \"{roles.get('witness_names', '')}\" method={roles.get('evidence', {}).get('role_method', {}).get('witness', 'unknown')}")
    print("=" * 60)
    
finally:
    db.close()
"@

try {
    docker compose exec -T api python -c $pythonScript
    Write-Host "[OK] Smoke test completed" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Smoke test failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host "END"
Write-Host "========================================"

