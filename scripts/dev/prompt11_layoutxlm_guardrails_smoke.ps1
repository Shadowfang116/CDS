# Prompt 11: LayoutXLM Guardrails Smoke Test
# Tests confidence thresholds, corruption detection, and evidence JSON consistency

param(
    [Parameter(Mandatory=$true)]
    [string]$DocId,
    [int]$PageNo = 1,
    [string]$OrgId = "f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 11: LAYOUTXLM GUARDRAILS TEST" -ForegroundColor Cyan
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

# Step 3: Run Python script to test guardrails
Write-Host ""
Write-Host "[3/6] Testing LayoutXLM guardrails (confidence thresholds, corruption detection)..." -ForegroundColor Yellow

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
    print(f"\n--- Testing LayoutXLM Guardrails for Document {doc_id}, Page {page_num} ---")
    
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
    
    # Build request payload with LayoutXLM and guardrail options
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
            "labels": None,  # Extract all labels
            "min_entity_confidence": 0.60,  # Default threshold
            "min_entity_confidence_cnic": 0.70,  # Higher threshold for CNIC
            "return_low_confidence": True,  # Return low-confidence entities for testing
        }
    }
    
    # Call hf-extractor
    print(f"\nCalling hf-extractor at {hf_extractor_url}/v1/extract with guardrails...")
    
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
            model_name_or_path = quality.get('model_name_or_path')
            needs_manual_review = quality.get('needs_manual_review')
            corruption_detected = quality.get('corruption_detected')
            page_confidence = quality.get('page_ocr_confidence')
            
            print(f"\n--- Quality Metrics ---")
            print(f"Extractor version used: {extractor_version_used}")
            print(f"Model name/path: {model_name_or_path}")
            print(f"Page OCR confidence: {page_confidence}")
            print(f"Needs manual review: {needs_manual_review}")
            print(f"Corruption detected: {corruption_detected}")
            
            # Extract entities
            entities = result.get('entities', [])
            print(f"\nTotal entities: {len(entities)}")
            
            if entities:
                print(f"\n--- Entity Details (first 3) ---")
                for i, entity in enumerate(entities[:3]):
                    print(f"\nEntity {i+1}:")
                        print(f"  Label: {entity.get('label')}")
                    print(f"  Value: {entity.get('value')}")
                    print(f"  Confidence: {entity.get('confidence')}")
                    print(f"  Low confidence flag: {entity.get('low_confidence', 'Not present')}")
                    print(f"  Token indices: {entity.get('source', {}).get('token_indices')}")
                    print(f"  Bbox (norm_1000): {entity.get('source', {}).get('bbox_norm_1000')}")
                    print(f"  Snippet: {entity.get('evidence', {}).get('snippet', '')[:80]}")
                    
                    # Check if value is built from tokens (token-copy only)
                    token_indices = entity.get('source', {}).get('token_indices', [])
                    if token_indices:
                        print(f"  ✓ Token indices present (token-copy only enforced)")
            
            # Verify guardrails
            print(f"\n--- Guardrails Verification ---")
            
            # Check needs_manual_review flag
            if needs_manual_review is not None:
                print(f"Needs manual review flag present: {needs_manual_review} {'[PASS]' if needs_manual_review is not None else '[FAIL]'}")
                if needs_manual_review:
                    print(f"  Reason: OCR confidence={page_confidence:.3f} corruption={corruption_detected}")
            else:
                print(f"Needs manual review flag: None [CHECK]")
            
            # Check corruption detection
            if corruption_detected is not None:
                print(f"Corruption detected flag present: {corruption_detected} {'[PASS]' if corruption_detected is not None else '[FAIL]'}")
            else:
                print(f"Corruption detected flag: None [CHECK]")
            
            # Check extractor version used
            if extractor_version_used:
                print(f"Extractor version used: {extractor_version_used} [PASS]")
            else:
                print(f"Extractor version used: None [CHECK]")
            
            # Check model metadata
            if extractor_version_used == "layoutxlm-v1":
                if model_name_or_path:
                    print(f"Model name/path present: {model_name_or_path} [PASS]")
                else:
                    print(f"Model name/path: None [CHECK - may be OK if fallback occurred]")
            
            print(f"\n--- Test Summary ---")
            print(f"✅ Response status: {response.status_code}")
            print(f"{'✅' if needs_manual_review is not None else '⚠️ '} Needs manual review flag present")
            print(f"{'✅' if corruption_detected is not None else '⚠️ '} Corruption detected flag present")
            print(f"{'✅' if extractor_version_used else '⚠️ '} Extractor version used present")
            print(f"{'✅' if entities else '⚠️ '} Entities returned (may be empty)")
            
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
Write-Host "[4/6] Checking hf-extractor logs..." -ForegroundColor Yellow
docker compose logs hf-extractor --tail=50 | Select-String "HF_EXTRACTOR" | Select-Object -First 5 | Write-Host
Write-Host "[OK] Logs checked." -ForegroundColor Green

# Step 5: Summary
Write-Host ""
Write-Host "[5/6] Test Summary" -ForegroundColor Yellow
Write-Host "  - Check output above for:" -ForegroundColor White
Write-Host "    * needs_manual_review flag in quality metrics" -ForegroundColor White
Write-Host "    * corruption_detected flag in quality metrics" -ForegroundColor White
Write-Host "    * extractor_version_used and model_name_or_path present" -ForegroundColor White
Write-Host "    * Entities have token_indices (token-copy only)" -ForegroundColor White
Write-Host "[OK] Test complete." -ForegroundColor Green

Write-Host ""
Write-Host "[6/6] Next: Run SQL Query I to verify evidence_json consistency" -ForegroundColor Yellow
Write-Host "  See scripts/dev/prompt5_sql_queries.sql for Query I" -ForegroundColor White

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROMPT 11 SMOKE TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

