# Prompt 9: LayoutXLM Fallback Smoke Test
# Tests that requesting LayoutXLM falls back to rules extraction when model not available

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,
    [int]$PageNo = 1,
    [string]$OrgId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 9: LAYOUTXLM FALLBACK TEST" -ForegroundColor Cyan
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

# Step 3: Run Python script to test LayoutXLM fallback
Write-Host ""
Write-Host "[3/6] Testing LayoutXLM fallback (requesting layoutxlm-v1 without model)..." -ForegroundColor Yellow

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
    print(f"\n--- Testing LayoutXLM Fallback for Document {doc_id}, Page {page_num} ---")
    
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
    
    # Build request payload with LayoutXLM requested (but model not available)
    payload = {
        "doc_id": str(doc_id),
        "page_no": page_num,
        "image": {
            "content_type": "image/png",
            "base64": image_base64
        },
        "ocr": None,  # No OCR provided - hf-extractor will run OCR
        "options": {
            "extractor_version": "layoutxlm-v1",  # Request LayoutXLM
            "enable_layoutxlm": True,  # Enable LayoutXLM gate
            "return_token_spans": True,
            "language_hint": "mixed",
            "labels": None  # Extract all labels
        }
    }
    
    # Call hf-extractor
    print(f"\nCalling hf-extractor at {hf_extractor_url}/v1/extract with extractor_version=layoutxlm-v1...")
    print(f"  (Expected: fallback to rules-v1 since model not mounted)")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{hf_extractor_url}/v1/extract",
                json=payload,
            )
            response.raise_for_status()
            
            result = response.json()
            
            print(f"\n--- Response Status: {response.status_code} ---")
            
            # Extract quality metrics
            quality = result.get('quality', {})
            extractor_version_used = quality.get('extractor_version_used')
            model_loaded = quality.get('model_loaded')
            model_name_or_path = quality.get('model_name_or_path')
            
            # Extract entities
            entities = result.get('entities', [])
            
            print(f"\n--- Quality Metrics ---")
            print(f"Extractor version used: {extractor_version_used}")
            print(f"Model loaded: {model_loaded}")
            print(f"Model name/path: {model_name_or_path}")
            print(f"Total entities: {len(entities)}")
            
            # Verify fallback behavior
            print(f"\n--- Fallback Verification ---")
            
            if response.status_code == 200:
                print(f"Status code: 200 [PASS]")
            else:
                print(f"Status code: {response.status_code} [FAIL]")
                sys.exit(1)
            
            if extractor_version_used == "rules-v1":
                print(f"Extractor version used: rules-v1 [PASS - fallback worked]")
            else:
                print(f"Extractor version used: {extractor_version_used} [CHECK - may be OK if model was loaded]")
            
            if model_loaded is False:
                print(f"Model loaded: False [PASS - expected since model not available]")
            elif model_loaded is True:
                print(f"Model loaded: True [CHECK - model was loaded successfully]")
            else:
                print(f"Model loaded: {model_loaded} [CHECK - None/unknown]")
            
            # Check if entities were returned (may be empty depending on page content)
            if entities:
                print(f"Entities returned: {len(entities)} [PASS - rules extraction worked]")
                sample = entities[0]
                print(f"\n--- Sample Entity ---")
                print(f"Label: {sample.get('label')}")
                print(f"Value: {sample.get('value')}")
                print(f"Confidence: {sample.get('confidence')}")
            else:
                print(f"Entities returned: 0 [CHECK - may be OK if page has no extractable entities]")
            
            print(f"\n--- Test Summary ---")
            print(f"✅ Response status: 200")
            print(f"{'✅' if extractor_version_used == 'rules-v1' else '⚠️ '} Extractor used: {extractor_version_used}")
            print(f"{'✅' if model_loaded is False else '⚠️ '} Model loaded: {model_loaded}")
            print(f"{'✅' if response.status_code == 200 else '❌'} Service did not crash")
            
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

# Step 4: Check hf-extractor logs for fallback
Write-Host ""
Write-Host "[4/6] Checking hf-extractor logs for LayoutXLM fallback..." -ForegroundColor Yellow
Write-Host "  Looking for HF_EXTRACTOR_MODEL lines with fallback_to_rules..." -ForegroundColor DarkYellow
$logLines = docker compose logs hf-extractor --tail=100 | Select-String "HF_EXTRACTOR_MODEL"
if ($logLines) {
    Write-Host $logLines -ForegroundColor Cyan
    $hasFallback = $logLines | Select-String "fallback_to_rules"
    if ($hasFallback) {
        Write-Host "[PASS] Found log line with fallback_to_rules" -ForegroundColor Green
    } else {
        Write-Host "[CHECK] Log line found but no fallback message (may be OK if model loaded)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] No HF_EXTRACTOR_MODEL log lines found in recent logs" -ForegroundColor Yellow
}

# Step 5: Check extraction logs
Write-Host ""
Write-Host "[5/6] Checking extraction logs..." -ForegroundColor Yellow
docker compose logs hf-extractor --tail=50 | Select-String "HF_EXTRACTOR_EXTRACT" | Select-Object -First 3 | Write-Host
Write-Host "[OK] Logs checked." -ForegroundColor Green

# Step 6: Summary
Write-Host ""
Write-Host "[6/6] Test Summary" -ForegroundColor Yellow
Write-Host "  - Check output above for:" -ForegroundColor White
Write-Host "    * Status code 200 (service did not crash)" -ForegroundColor White
Write-Host "    * extractor_version_used == 'rules-v1' (fallback occurred)" -ForegroundColor White
Write-Host "    * model_loaded == false (model not available)" -ForegroundColor White
Write-Host "    * Entities returned (may be empty depending on page)" -ForegroundColor White
Write-Host "  - Check logs for 'HF_EXTRACTOR_MODEL fallback_to_rules' line" -ForegroundColor White
Write-Host "[OK] Test complete." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 9 SMOKE TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

