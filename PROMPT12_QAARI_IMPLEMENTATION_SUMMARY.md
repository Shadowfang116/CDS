# Prompt 12: Qaari OCR Fallback Implementation Summary

## Overview
Implemented optional Urdu-heavy OCR fallback using `oddadmix/Qaari-0.1-Urdu-OCR-VL-2B-Instruct` inside hf-extractor, enabled only when explicitly configured AND only when baseline OCR quality is poor. Also added span-offset evidence support end-to-end so that when OCR comes from a text-only engine (Qaari), entities can still carry precise evidence without requiring bounding boxes.

## Key Constraints Met
- ✅ Local-only. No external APIs.
- ✅ Qaari is OPTIONAL and disabled by default.
- ✅ Keep api/worker ML-free; ML deps only in hf-extractor, and only installed if build arg enabled.
- ✅ No hallucination policy: extracted entity values must be assembled strictly from OCR tokens.
- ✅ Quality gates: when Qaari is used OR when entity has no bbox evidence, mark needs_manual_review=true.

## Changes Made

### A) Schemas (`backend/hf_extractor/schemas.py`)
- **ExtractedEntity**: Added `span_start` and `span_end` (Optional[int]) to EntitySource
- **EntitySource**: Made `bbox` and `bbox_norm_1000` optional (None for text-only OCR)
- **OCRData**: Made `boxes` optional (None for text-only OCR)
- **ExtractOptions**: Added `enable_qaari` (bool, default False) and `qaari_model_name_or_path` (Optional[str])
- **QualityMetrics**: Added `qaari_used`, `ocr_text_only`, and `qaari_model_name_or_path` fields

### B) Qaari OCR Module (`backend/hf_extractor/ocr_qaari.py`) - NEW
- Created new module with `qaari_transcribe()` function
- Safe imports inside function (transformers/torch)
- Module-level caching for model + processor
- Deterministic transcription-only prompting
- Confidence heuristic: `min(0.70, max(0.30, len(text)/2000))`
- Returns text-only OCR (no bounding boxes)

### C) OCR Router (`backend/hf_extractor/ocr_router.py`)
- Added Qaari fallback routing logic
- Checks `enable_qaari` from options or `HF_ENABLE_QAARI` env var
- Gets model path from options or `HF_QAARI_MODEL_PATH` env var
- Invokes Qaari only when baseline OCR confidence < threshold OR word_count < 10
- Returns OCRData with `boxes=None` and `ocr_text_only=True` when Qaari is used
- Includes Qaari metadata in routing result

### D) Extractors (`backend/hf_extractor/extractors.py`)
- Updated `_compute_bbox_union()` to return `None` when boxes are missing
- Added `_compute_span_offsets()` function to compute character offsets in page text
- Updated all extractor functions to accept `Optional[List[List[float]]]` for boxes
- All extractors now compute span offsets when boxes is None
- Updated `extract_all_entities()` to handle boxes=None

### E) LayoutXLM Inference (`backend/hf_extractor/layoutxlm_infer.py`)
- Added check to skip LayoutXLM if boxes are None (text-only OCR)
- Logs warning and falls back to rules-v1 automatically

### F) Main Service (`backend/hf_extractor/main.py`)
- Extracts Qaari flags from OCR routing result
- Handles `boxes=None` case for OCRData
- Propagates `qaari_used`, `ocr_text_only`, and `qaari_model_name_or_path` to quality metrics
- Sets `needs_manual_review=True` when Qaari is used OR ocr_text_only is True
- Includes span offsets in entity source when bbox is None
- Updated logging to include Qaari metadata

### G) Client (`backend/app/services/extractors/hf_extractor_client.py`)
- Parses `span_start` and `span_end` from entity source
- Attaches Qaari metadata (`qaari_used`, `ocr_text_only`, `qaari_model_name_or_path`) to quality_metadata

### H) Persistence (`backend/app/services/dossier_autofill.py`)
- Persists `span_start` and `span_end` in evidence_json
- Persists `qaari_used`, `ocr_text_only`, and `qaari_model_name_or_path` in evidence_json
- Made `bbox` and `bbox_norm_1000` optional in evidence_json (can be None)

### I) UI (`frontend/components/ocr/OCRExtractionsPanel.tsx`)
- Evidence modal displays span offsets when bbox is null
- Shows "Evidence: Text Span Offsets" with start/end character positions
- Maintains existing bbox display path when bbox exists

### J) Docker Configuration
- **requirements-vlm.txt** (NEW): Contains transformers, torch, pillow, sentencepiece
- **Dockerfile**: Added `INSTALL_VLM_DEPS` build arg (default 0)
- Conditionally installs VLM dependencies only when `INSTALL_VLM_DEPS=1`
- **docker-compose.yml**: Added environment variables:
  - `HF_ENABLE_QAARI` (default: false)
  - `HF_QAARI_MODEL_PATH` (default: empty)

### K) Smoke Test (`scripts/dev/prompt12_qaari_fallback_smoke.ps1`) - NEW
- Tests Qaari fallback with forced poor baseline OCR
- Verifies `qaari_used=true` and `ocr_text_only=true` in response
- Checks that entities include `span_start`/`span_end` when bbox is null
- Validates `needs_manual_review=true` when Qaari is used

## Usage

### Building with VLM Dependencies
```powershell
# Set environment variable
$env:INSTALL_VLM_DEPS = "1"

# Rebuild hf-extractor
docker compose build hf-extractor

# Or rebuild all services
docker compose build
```

### Enabling Qaari OCR
```powershell
# Set environment variables
$env:HF_ENABLE_QAARI = "true"
$env:HF_QAARI_MODEL_PATH = "oddadmix/Qaari-0.1-Urdu-OCR-VL-2B-Instruct"
$env:HF_DEVICE = "cpu"  # or "cuda" if GPU available

# Restart hf-extractor
docker compose up -d --force-recreate hf-extractor
```

### Running Smoke Test
```powershell
# Set Qaari model path
$env:HF_QAARI_MODEL_PATH = "oddadmix/Qaari-0.1-Urdu-OCR-VL-2B-Instruct"

# Run smoke test
.\scripts\dev\prompt12_qaari_fallback_smoke.ps1
```

## Acceptance Criteria Verification

1. ✅ **When Qaari disabled (default), behavior unchanged**
   - Qaari is disabled by default (`enable_qaari=False`)
   - No VLM dependencies installed unless `INSTALL_VLM_DEPS=1`
   - Existing OCR routing continues to work as before

2. ✅ **When Qaari enabled and baseline OCR is low-quality, hf-extractor uses Qaari and marks needs_manual_review=true**
   - Qaari is invoked when baseline confidence < threshold OR word_count < 10
   - `qaari_used=true` and `ocr_text_only=true` in quality metrics
   - `needs_manual_review=true` is set

3. ✅ **Entities from Qaari path have span_start/span_end and snippet; bbox fields are null**
   - Entities have `span_start` and `span_end` character offsets
   - `bbox` and `bbox_norm_1000` are `None` (not fabricated)
   - Snippet is still provided from OCR words

4. ✅ **UI evidence modal displays span offsets when bbox missing**
   - Evidence modal shows "Evidence: Text Span Offsets" when bbox is null
   - Displays start and end character positions
   - Falls back to bbox display when bbox exists

## Files Modified
- `backend/hf_extractor/schemas.py`
- `backend/hf_extractor/ocr_router.py`
- `backend/hf_extractor/extractors.py`
- `backend/hf_extractor/layoutxlm_infer.py`
- `backend/hf_extractor/main.py`
- `backend/hf_extractor/Dockerfile`
- `backend/app/services/extractors/hf_extractor_client.py`
- `backend/app/services/dossier_autofill.py`
- `frontend/components/ocr/OCRExtractionsPanel.tsx`
- `docker-compose.yml`

## Files Created
- `backend/hf_extractor/ocr_qaari.py`
- `backend/hf_extractor/requirements-vlm.txt`
- `scripts/dev/prompt12_qaari_fallback_smoke.ps1`

## Testing
Run the smoke test script to verify Qaari fallback functionality:
```powershell
.\scripts\dev\prompt12_qaari_fallback_smoke.ps1
```

The test verifies:
- Qaari is invoked when baseline OCR is poor
- Quality flags are set correctly
- Entities have span offsets when bbox is null
- needs_manual_review is set appropriately

