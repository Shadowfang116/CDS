# Prompt 7: HF Extractor Image-Only Smoke Test
# Tests that hf-extractor can run end-to-end on page images alone

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,
    [int]$PageNo = 1,
    [string]$CaseId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8",
    [string]$OrgId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 7: HF EXTRACTOR IMAGE-ONLY TEST" -ForegroundColor Cyan
Write-Host "Document ID: $DocId, Page: $PageNo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker engine
Write-Host "[1/5] Checking Docker engine..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Docker engine is not running." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Docker not found or engine not running." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker engine is reachable" -ForegroundColor Green

# Step 2: Ensure hf-extractor container is up
Write-Host ""
Write-Host "[2/5] Ensuring hf-extractor container is up..." -ForegroundColor Yellow
try {
    docker compose up -d hf-extractor 2>&1 | Out-String | Write-Host
    Write-Host "[OK] hf-extractor container is running" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Failed to start hf-extractor: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Run Python script to get page image and call hf-extractor
Write-Host ""
Write-Host "[3/5] Running Python script to get page image and call hf-extractor..." -ForegroundColor Yellow

$pythonScript = @"
import sys
import os
import uuid
import base64
import json
import httpx
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.core.config import settings
from app.models.document import DocumentPage
from app.services.documents.pdf_render import get_page_image_bytes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

doc_id = uuid.UUID(os.environ.get('DOC_ID'))
page_num = int(os.environ.get('PAGE_NO', '1'))
org_id = uuid.UUID(os.environ.get('ORG_ID'))
hf_extractor_url = os.getenv('HF_EXTRACTOR_URL', 'http://hf-extractor:8090')

# Database setup
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

with SessionLocal() as db:
    print(f"\n--- Processing Document {doc_id}, Page {page_num} ---")
    
    # Fetch page from DB
    page = db.query(DocumentPage).filter(
        DocumentPage.org_id == org_id,
        DocumentPage.document_id == doc_id,
        DocumentPage.page_number == page_num,
    ).first()
    
    if not page:
        print(f"ERROR: Page {page_num} not found for document {doc_id}")
        sys.exit(1)
    
    print(f"Found page: minio_key={page.minio_key_page_pdf}")
    
    # Get page image bytes
    print(f"Rendering page image from PDF...")
    image_bytes = get_page_image_bytes(page.minio_key_page_pdf)
    
    if not image_bytes:
        print(f"ERROR: Failed to render page image")
        sys.exit(1)
    
    print(f"Page image size: {len(image_bytes)} bytes")
    
    # Encode to base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Build request payload (image-only, no OCR)
    payload = {
        "doc_id": str(doc_id),
        "page_no": page_num,
        "image": {
            "content_type": "image/png",
            "base64": image_base64
        },
        "ocr": None,  # No OCR provided - hf-extractor will run OCR
        "options": {
            "extractor_version": "layoutxlm-v1",
            "return_token_spans": True,
            "language_hint": "mixed",
            "labels": None  # Extract all labels
        }
    }
    
    # Call hf-extractor
    print(f"\nCalling hf-extractor at {hf_extractor_url}/v1/extract...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{hf_extractor_url}/v1/extract",
                json=payload,
            )
            response.raise_for_status()
            
            result = response.json()
            
            print(f"\n--- Response Status: {response.status_code} ---")
            print(f"Total entities: {len(result.get('entities', []))}")
            
            # Count entities by label
            entities_by_label = {}
            for entity in result.get('entities', []):
                label = entity.get('label', 'UNKNOWN')
                entities_by_label[label] = entities_by_label.get(label, 0) + 1
            
            print(f"Entities by label: {entities_by_label}")
            
            # Show sample entity
            if result.get('entities'):
                sample = result['entities'][0]
                print(f"\n--- Sample Entity (first) ---")
                print(f"Label: {sample.get('label')}")
                print(f"Value: {sample.get('value')}")
                print(f"Confidence: {sample.get('confidence')}")
                print(f"Bbox (px): {sample.get('source', {}).get('bbox')}")
                print(f"Bbox (norm_1000): {sample.get('source', {}).get('bbox_norm_1000')}")
                print(f"Token indices: {sample.get('source', {}).get('token_indices')}")
                print(f"Snippet: {sample.get('evidence', {}).get('snippet', '')[:80]}")
            
            print(f"\nQuality metrics:")
            quality = result.get('quality', {})
            print(f"  Page corrupted: {quality.get('page_corrupted')}")
            print(f"  Page OCR confidence: {quality.get('page_ocr_confidence')}")
            
            # Verify bbox_norm_1000 is present
            all_have_bbox_norm = all(
                e.get('source', {}).get('bbox_norm_1000') is not None
                for e in result.get('entities', [])
            )
            
            if all_have_bbox_norm:
                print(f"\n[PASS] All entities have bbox_norm_1000")
            else:
                print(f"\n[FAIL] Some entities missing bbox_norm_1000")
            
            print(f"\n--- Test Summary ---")
            print(f"Status Code: {response.status_code} {'[PASS]' if response.status_code == 200 else '[FAIL]'}")
            print(f"Entities Returned: {len(result.get('entities', []))} {'[PASS]' if result.get('entities') else '[CHECK - No entities, but no errors]'}")
            print(f"Bbox_norm_1000 Present: {all_have_bbox_norm} {'[PASS]' if all_have_bbox_norm else '[FAIL]'}")
            
    except httpx.HTTPStatusError as e:
        print(f"ERROR: HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

sys.exit(0)
"@

$env:DOC_ID = $DocId
$env:PAGE_NO = $PageNo
$env:ORG_ID = $OrgId

docker compose exec -e DOC_ID=$DocId -e PAGE_NO=$PageNo -e ORG_ID=$OrgId api python -c $pythonScript | Write-Host

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host "[OK] Python script executed successfully." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Python script exited with code $exitCode" -ForegroundColor Red
    exit $exitCode
}

# Step 4: Check hf-extractor logs
Write-Host ""
Write-Host "[4/5] Checking hf-extractor logs for OCR activity..." -ForegroundColor Yellow
docker compose logs hf-extractor --tail=50 | Select-String "OCR|EXTRACT" | Write-Host
Write-Host "[OK] Logs checked." -ForegroundColor Green

# Step 5: Summary
Write-Host ""
Write-Host "[5/5] Test Summary" -ForegroundColor Yellow
Write-Host "  - Check output above for:" -ForegroundColor White
Write-Host "    * Status code 200" -ForegroundColor White
Write-Host "    * Entities returned (or clear '0 entities' message)" -ForegroundColor White
Write-Host "    * bbox_norm_1000 present on all entities" -ForegroundColor White
Write-Host "  - Check logs for 'OCR needed' or 'used_ocr_engine=tesseract'" -ForegroundColor White
Write-Host "[OK] Test complete." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 7 SMOKE TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

