# Prompt 6: OCR Fallback Smoke Test
# Tests mojibake detection, repair, and re-OCR fallback
# Usage: .\scripts\dev\prompt6_ocr_fallback_smoke.ps1 -DocId "550e8400-e29b-41d4-a716-446655440000"

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId
)

Write-Host "=== Prompt 6: OCR Fallback Smoke Test ===" -ForegroundColor Cyan
Write-Host "Document ID: $DocId" -ForegroundColor Yellow
Write-Host ""

# Test pages 1-8
$pages = 1..8

Write-Host "Step 1: Query OCR page data BEFORE fallback" -ForegroundColor Green
Write-Host ""

# Query before state
docker compose exec -T db psql -U bank_diligence -d bank_diligence -c @"
SELECT 
    page_number,
    LEFT(ocr_text, 80) AS text_preview,
    LENGTH(ocr_text) AS text_len,
    ocr_confidence,
    ocr_engine,
    ocr_status
FROM document_pages
WHERE document_id = '$DocId'
    AND page_number BETWEEN 1 AND 8
ORDER BY page_number;
"@

Write-Host ""
Write-Host "Step 2: Run get_page_text_with_fallback for each page (via Python)" -ForegroundColor Green
Write-Host ""

# Create Python script to test fallback (write directly to container)
$pythonScript = @"
import sys
import os
sys.path.insert(0, '/app')

from app.db.session import get_db
from app.services.ocr_fallback import get_page_text_with_fallback
import uuid

doc_id = uuid.UUID('$DocId')
org_id = uuid.UUID('00000000-0000-0000-0000-000000000000')

# Get org_id from document
from app.models.document import Document
db = next(get_db())
doc = db.query(Document).filter(Document.id == doc_id).first()
if doc:
    org_id = doc.org_id
    print(f'Using org_id: {org_id}')
else:
    print(f'ERROR: Document {doc_id} not found')
    sys.exit(1)

for page_num in range(1, 9):
    try:
        text = get_page_text_with_fallback(
            db=db,
            org_id=org_id,
            document_id=doc_id,
            page_number=page_num,
            use_corrections=True
        )
        preview = text[:80] if text else ''
        print(f'Page {page_num}: len={len(text)} preview=\"{preview}\"')
    except Exception as e:
        print(f'Page {page_num}: ERROR - {str(e)}')

db.close()
"@

Write-Host "Running Python script in api container..."
$pythonScript | docker compose exec -T api python3 -

Write-Host ""
Write-Host "Step 3: Query OCR page data AFTER fallback (to show persistence)" -ForegroundColor Green
Write-Host ""

# Query after state
docker compose exec -T db psql -U bank_diligence -d bank_diligence -c @"
SELECT 
    page_number,
    LEFT(ocr_text, 80) AS text_preview,
    LENGTH(ocr_text) AS text_len,
    ocr_confidence,
    ocr_engine,
    ocr_status
FROM document_pages
WHERE document_id = '$DocId'
    AND page_number BETWEEN 1 AND 8
ORDER BY page_number;
"@

Write-Host ""
Write-Host "Step 4: Test party roles extraction" -ForegroundColor Green
Write-Host ""

# Create Python script to test party roles
$partyRolesScript = @"
import sys
import os
sys.path.insert(0, '/app')

from app.db.session import get_db
from app.services.extractors.party_roles import extract_party_roles_from_document, PageOCR
from app.services.ocr_fallback import get_page_text_with_fallback
from app.models.document import Document, DocumentPage
import uuid

doc_id = uuid.UUID('$DocId')
org_id = uuid.UUID('00000000-0000-0000-0000-000000000000')

db = next(get_db())
doc = db.query(Document).filter(Document.id == doc_id).first()
if doc:
    org_id = doc.org_id
    print(f'Document: {doc.original_filename}')
else:
    print(f'ERROR: Document {doc_id} not found')
    sys.exit(1)

# Build PageOCR list using get_page_text_with_fallback
pages = db.query(DocumentPage).filter(
    DocumentPage.document_id == doc_id,
    DocumentPage.org_id == org_id,
    DocumentPage.ocr_status == 'Done'
).order_by(DocumentPage.page_number).all()

doc_pages_ocr = []
for page in pages:
    text = get_page_text_with_fallback(
        db=db,
        org_id=org_id,
        document_id=doc_id,
        page_number=page.page_number,
        use_corrections=True
    )
    doc_pages_ocr.append(PageOCR(
        document_id=str(doc_id),
        document_name=doc.original_filename or '',
        page_number=page.page_number,
        text=text
    ))

# Extract party roles
roles = extract_party_roles_from_document(doc_pages_ocr)

print(f'Seller: \"{roles.get(\"seller_names\", \"\")}\"')
print(f'Buyer: \"{roles.get(\"buyer_names\", \"\")}\"')
print(f'Witness: \"{roles.get(\"witness_names\", \"\")}\"')

db.close()
"@

Write-Host "Running party roles extraction..."
$partyRolesScript | docker compose exec -T api python3 -

Write-Host ""
Write-Host "Step 5: Check logs for OCR_FALLBACK entries" -ForegroundColor Green
Write-Host ""

docker compose logs api --tail=100 | Select-String "OCR_FALLBACK:"

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Expected results:"
Write-Host "- OCR_FALLBACK: action=REPAIR or action=RE_OCR in logs for corrupted pages"
Write-Host "- OCR text persisted back to DB (engine shows +repaired or urd_fallback)"
Write-Host "- Party roles extraction returns proper Urdu names (not mojibake)"
Write-Host "- Valid names should be accepted, mojibake should be rejected"
