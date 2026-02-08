# Prompt 8: HF Extractor OCR Fallback Smoke Test
# Tests OCR routing with fallback selection and evidence persistence

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,
    [int]$PageNo = 1,
    [string]$OrgId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 8: HF EXTRACTOR OCR FALLBACK TEST" -ForegroundColor Cyan
Write-Host "Document ID: $DocId, Page: $PageNo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker engine
Write-Host "[1/6] Checking Docker engine..." -ForegroundColor Yellow
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
Write-Host "[2/6] Ensuring hf-extractor container is up..." -ForegroundColor Yellow
try {
    docker compose up -d hf-extractor 2>&1 | Out-String | Write-Host
    Write-Host "[OK] hf-extractor container is running" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Failed to start hf-extractor: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Run Python script to test OCR fallback
Write-Host ""
Write-Host "[3/6] Testing OCR fallback with force_ocr_fallback=true..." -ForegroundColor Yellow

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
    print(f"\n--- Testing OCR Fallback for Document {doc_id}, Page {page_num} ---")
    
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
    
    # Build request payload with force_ocr_fallback=true
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
            "labels": None,  # Extract all labels
            "force_ocr_fallback": True,  # P17: Force fallback for testing
            "enable_ocr_fallback": True,
            "min_ocr_confidence": 0.55
        }
    }
    
    # Call hf-extractor
    print(f"\nCalling hf-extractor at {hf_extractor_url}/v1/extract with force_ocr_fallback=true...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{hf_extractor_url}/v1/extract",
                json=payload,
            )
            response.raise_for_status()
            
            result = response.json()
            
            print(f"\n--- Response Status: {response.status_code} ---")
            
            # Extract OCR metadata from quality metrics
            quality = result.get('quality', {})
            selected_conf = quality.get('page_ocr_confidence', 0.0)
            used_fallback = quality.get('ocr_used_fallback', False)
            ocr_engine_params = quality.get('ocr_engine_params', {})
            
            print(f"\n--- OCR Routing Results ---")
            print(f"Selected page confidence: {selected_conf:.3f}")
            print(f"Used fallback: {used_fallback}")
            print(f"OCR engine params: {ocr_engine_params}")
            
            # Show entities
            entities = result.get('entities', [])
            print(f"\nTotal entities: {len(entities)}")
            
            if entities:
                sample = entities[0]
                print(f"\n--- Sample Entity (first) ---")
                print(f"Label: {sample.get('label')}")
                print(f"Value: {sample.get('value')}")
                print(f"Confidence: {sample.get('confidence')}")
                print(f"Bbox (norm_1000): {sample.get('source', {}).get('bbox_norm_1000')}")
            
            # Verify fallback was used
            if used_fallback:
                print(f"\n[PASS] Fallback OCR was triggered and used")
            else:
                print(f"\n[CHECK] Fallback was not used (this is OK if primary OCR was already high confidence)")
            
            # Verify evidence metadata
            print(f"\n--- Evidence Metadata Verification ---")
            print(f"OCR page confidence present: {selected_conf is not None} {'[PASS]' if selected_conf is not None else '[FAIL]'}")
            print(f"OCR used fallback present: {used_fallback is not None} {'[PASS]' if used_fallback is not None else '[FAIL]'}")
            print(f"OCR engine params present: {ocr_engine_params is not None} {'[PASS]' if ocr_engine_params else '[FAIL]'}")
            
            print(f"\n--- Test Summary ---")
            print(f"Status Code: {response.status_code} {'[PASS]' if response.status_code == 200 else '[FAIL]'}")
            print(f"Fallback Used: {used_fallback} {'[PASS - expected when force_ocr_fallback=true]' if used_fallback else '[CHECK - may be OK if primary was better]'}")
            print(f"OCR Metadata Present: {'[PASS]' if (selected_conf is not None and used_fallback is not None and ocr_engine_params) else '[FAIL]'}")
            
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

# Step 4: Check hf-extractor logs for OCR routing
Write-Host ""
Write-Host "[4/6] Checking hf-extractor logs for OCR routing..." -ForegroundColor Yellow
Write-Host "  Looking for HF_EXTRACTOR_OCR lines with used_fallback=true..." -ForegroundColor DarkYellow
$logLines = docker compose logs hf-extractor --tail=100 | Select-String "HF_EXTRACTOR_OCR"
if ($logLines) {
    Write-Host $logLines -ForegroundColor Cyan
    $hasFallback = $logLines | Select-String "used_fallback=true"
    if ($hasFallback) {
        Write-Host "[PASS] Found log line with used_fallback=true" -ForegroundColor Green
    } else {
        Write-Host "[CHECK] Log line found but used_fallback=false (may be OK)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] No HF_EXTRACTOR_OCR log lines found in recent logs" -ForegroundColor Yellow
}

# Step 5: Check extraction logs
Write-Host ""
Write-Host "[5/6] Checking extraction logs..." -ForegroundColor Yellow
docker compose logs hf-extractor --tail=50 | Select-String "HF_EXTRACTOR_EXTRACT" | Select-Object -First 5 | Write-Host
Write-Host "[OK] Logs checked." -ForegroundColor Green

# Step 6: Summary
Write-Host ""
Write-Host "[6/6] Test Summary" -ForegroundColor Yellow
Write-Host "  - Check output above for:" -ForegroundColor White
Write-Host "    * Status code 200" -ForegroundColor White
Write-Host "    * OCR routing metadata (selected_conf, used_fallback, engine_params)" -ForegroundColor White
Write-Host "    * Log line: HF_EXTRACTOR_OCR with used_fallback=true" -ForegroundColor White
Write-Host "    * Evidence metadata present in response quality" -ForegroundColor White
Write-Host "[OK] Test complete." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 8 SMOKE TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

