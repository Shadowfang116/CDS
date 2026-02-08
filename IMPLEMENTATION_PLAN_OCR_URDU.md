# E2E UPGRADE — Urdu OCR Quality + Party Role Extraction
## Implementation Plan — Prompt 1/12

---

## A) CURRENT OCR PIPELINE MAP

### 1. API Route: Enqueue OCR
**File:** `backend/app/api/routes/ocr.py`
**Function:** `enqueue_document_ocr()` (lines 70-126)
```python
@router.post("/documents/{document_id}/ocr", response_model=OCREnqueueResponse)
async def enqueue_document_ocr(...):
    task = process_document_ocr.apply_async(
        args=[str(document_id), str(org_id), str(user_id)],
        kwargs={"force": force},
    )
```
- **Entry point:** `POST /api/v1/documents/{document_id}/ocr`
- **Action:** Enqueues Celery task `ocr.process_document`
- **Audit:** Logs `document.ocr_enqueued`

### 2. Worker Task: Process Document OCR
**File:** `backend/app/workers/tasks_ocr.py`
**Function:** `process_document_ocr()` (lines 37-207)
```python
@celery_app.task(name="ocr.process_document", bind=True, max_retries=3)
def process_document_ocr(self, document_id: str, org_id: str, user_id: str, force: bool = False):
    # Process each page
    text, confidence, ocr_metadata = ocr_page_pdf(page.minio_key_page_pdf)
    page.ocr_text = text
    page.ocr_confidence = confidence
    page.ocr_status = "Done"
```
- **Action:** Iterates through document pages, calls `ocr_page_pdf()` for each
- **Storage:** Updates `document_pages.ocr_text`, `document_pages.ocr_confidence`, `document_pages.ocr_status`

### 3. OCR Service: Main Pipeline
**File:** `backend/app/services/ocr.py`
**Function:** `ocr_page_pdf()` (lines 176-204)
```python
def ocr_page_pdf(minio_key: str) -> Tuple[str, Optional[float], dict]:
    pdf_bytes = download_page_pdf(minio_key)
    image = pdf_to_image(pdf_bytes)
    text, confidence, metadata = run_tesseract(image)
    return text, confidence, metadata
```
- **Steps:**
  1. `download_page_pdf()`: Downloads PDF bytes from MinIO
  2. `pdf_to_image()`: Converts PDF to PIL Image using `pdf2image.convert_from_bytes()` at `settings.OCR_DPI` (default 300)
  3. `run_tesseract()`: Runs OCR on the image

### 4. PDF to Image Conversion
**File:** `backend/app/services/ocr.py`
**Function:** `pdf_to_image()` (lines 41-50)
```python
def pdf_to_image(pdf_bytes: bytes) -> Image.Image:
    images = convert_from_bytes(pdf_bytes, dpi=settings.OCR_DPI, fmt="png")
    return images[0]
```
- **Library:** `pdf2image` (uses poppler's `pdftoppm`)
- **DPI:** `settings.OCR_DPI` = 300 (configurable in `app/core/config.py`)

### 5. Image Preprocessing
**File:** `backend/app/services/ocr.py`
**Function:** `preprocess_image()` (lines 53-126)
```python
def preprocess_image(image: Image.Image) -> Image.Image:
    if not settings.OCR_ENABLE_PREPROCESS:
        return image
    # Convert to grayscale
    image = image.convert('L')
    # Auto-contrast
    image = ImageOps.autocontrast(image)
    # Light denoise (median filter)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    # Resize if too large/small
    # Simple adaptive threshold (percentile-based, requires numpy)
```
- **Status:** Basic preprocessing exists but limited:
  - ✅ Grayscale conversion
  - ✅ Auto-contrast
  - ✅ Light denoising (median filter)
  - ✅ Resize logic
  - ⚠️ Adaptive threshold (optional, requires numpy - not in dependencies)
  - ❌ No deskew
  - ❌ No margin cropping
  - ❌ No background shading removal
  - ❌ No explicit contrast enhancement beyond auto-contrast

### 6. Tesseract OCR Execution
**File:** `backend/app/services/ocr.py`
**Function:** `run_tesseract()` (lines 129-173)
```python
def run_tesseract(image: Image.Image) -> Tuple[str, Optional[float], dict]:
    processed_image = preprocess_image(image)
    lang = settings.OCR_LANG  # Default: "eng"
    config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM} -l {lang_used}"
    text = pytesseract.image_to_string(processed_image, config=config, timeout=...)
    # Get confidence from pytesseract.image_to_data()
```
- **Parameters:**
  - `OCR_LANG`: Default `"eng"` (configurable, but Urdu not installed)
  - `OCR_PSM`: Default `6` (uniform block of text)
  - `OCR_OEM`: Default `1` (LSTM only)
- **Language handling:** Checks if "urd" is in lang, falls back to "eng" if not available
- **Confidence:** Heuristic average from Tesseract word confidence scores

### 7. Configuration
**File:** `backend/app/core/config.py` (lines 61-69)
```python
OCR_DPI: int = 300
OCR_LANG: str = "eng"
OCR_PSM: int = 6
OCR_OEM: int = 1
OCR_IMAGE_MAX_SIDE: int = 2200
OCR_TIMEOUT_SECONDS: int = 120
OCR_ENABLE_PREPROCESS: bool = True
```

### 8. Storage
**Table:** `document_pages`
- `ocr_text` (Text, nullable)
- `ocr_confidence` (Numeric, nullable)
- `ocr_status` (String: "Queued", "Processing", "Done", "Failed")
- `ocr_started_at`, `ocr_finished_at` (DateTime)

---

## B) CURRENT EXTRACTION PIPELINE MAP

### 1. Autofill Service Entry Point
**File:** `backend/app/services/dossier_autofill.py`
**Function:** `autofill_dossier()` (lines 326-646)
- **Called from:** `POST /api/v1/cases/{case_id}/dossier/autofill` (`backend/app/api/routes/dossier_autofill.py`)
- **Input:** Collects all OCR text from `document_pages` where `ocr_status == "Done"`
- **Process:** Runs extractors for each field type, collects best extractions, creates `OCRExtractionCandidate` rows

### 2. Current Extractors (Inline Functions)
**File:** `backend/app/services/dossier_autofill.py`
- `extract_plot_number()` (lines 45-68)
- `extract_block()` (lines 71-91)
- `extract_phase()` (lines 94-113)
- `extract_scheme_name()` (lines 117-150)
- `extract_location_fields()` (lines 151-188)
- `extract_khasra_numbers()` (lines 187-210)
- `extract_registry_fields()` (lines 212-253)
- `extract_estamp_id()` (lines 255-281)

### 3. Name Extraction (External Module)
**File:** `backend/app/services/extractors/name_lines.py`
**Function:** `extract_name_lines()` (lines 50-158)
- **Usage:** Called in `autofill_dossier()` line 460
- **Current field:** Only `party.name.raw` (line 462)
- **Method:** Filters OCR lines using heuristics (length, digits, stopwords, sentence verbs, token count, alphabetic ratio)
- **Returns:** `List[NameLineResult]` with value, snippet, score, flags

### 4. Field Validators
**File:** `backend/app/services/extractors/validators.py`
**Function:** `get_field_validator()` (lines 262-280)
- **Registration:** Pattern-based matching on field_key:
  - `'name' in field_key.lower()` → `is_probably_name_line`
  - `'cnic' in field_key.lower()` → `validate_cnic`
  - `'plot' in field_key.lower()` → `validate_plot`
  - `'khasra' in field_key.lower()` → `validate_khasra_list`
  - `'registry' in field_key.lower() and 'number' in field_key.lower()` → `validate_registry_number`
  - `'estamp' in field_key.lower()` → `validate_estamp`
- **Validation:** Applied in `autofill_dossier()` lines 564-586 before creating candidates

### 5. Candidate Creation
**File:** `backend/app/services/dossier_autofill.py` (lines 511-631)
```python
for ef in extracted_fields:
    # Deduplication
    # Validation
    # Quality check
    new_candidate = OCRExtractionCandidate(
        field_key=ef.field_path,
        proposed_value=validated_value,
        confidence=ef.confidence,
        snippet=ef.evidence.get("snippet"),
        status="Pending",
        ...
    )
    db.add(new_candidate)
```

### 6. Current Fields Extracted
From `autofill_dossier()` (lines 404-475):
- `property.plot_number`
- `property.block`
- `property.phase`
- `property.scheme_name`
- `property.location.*` (city, district, tehsil, mouza)
- `property.khasra_numbers`
- `registry.*` (registry_number, book_number, volume_number, page_number)
- `stamp.estamp_id_or_number`
- `party.name.raw` (single field, uses `extract_name_lines()`)

### 7. Frontend Display
**File:** `frontend/components/ocr/OCRExtractionsPanel.tsx`
- Displays `OCRExtractionCandidate` items with field_key, proposed_value, confidence, snippet
- Supports Confirm/Reject/Override actions
- Field keys are string-based, no hardcoded list

**File:** `frontend/components/case/DossierFieldsEditor.tsx` (lines 15-33)
- Hardcoded field lists for display (property.*, party.name.*)
- Already includes `party.name.seller` in display list but not extracted yet

---

## C) GAP ANALYSIS

### Missing for Urdu OCR Improvements:

1. **Rendering DPI Control**
   - ✅ **Status:** Present but fixed at 300 DPI
   - **Gap:** No dynamic DPI adjustment (300-400 range)
   - **Location:** `backend/app/services/ocr.py:pdf_to_image()` line 45

2. **Advanced Preprocessing**
   - ⚠️ **Status:** Basic preprocessing exists
   - **Gaps:**
     - ❌ Deskew (rotation correction)
     - ❌ Advanced denoising (bilateral filter, non-local means)
     - ❌ Explicit contrast enhancement (beyond auto-contrast)
     - ❌ Margin cropping (remove white/grey borders)
     - ❌ Background shading removal (morphological operations)
   - **Location:** `backend/app/services/ocr.py:preprocess_image()` (lines 53-126)
   - **Dependencies:** OpenCV (`cv2`) not installed (numpy is optional, not in dependencies)

3. **Language Packs**
   - ❌ **Status:** Urdu not installed
   - **Command output:**
     ```
     tesseract --list-langs
     List of available languages: eng, osd
     ```
   - **Gap:** Need `tesseract-ocr-urd` package
   - **Location:** `backend/Dockerfile` (line 5: `tesseract-ocr`)

4. **Script Detection**
   - ❌ **Status:** Not implemented
   - **Gap:** No method to detect Urdu vs English dominance in page/region
   - **Location:** New file needed: `backend/app/services/ocr_script_detect.py` (or similar)

5. **Language-Aware OCR Execution**
   - ⚠️ **Status:** Language selection exists but is static
   - **Gap:** No dynamic language selection based on script detection
   - **Location:** `backend/app/services/ocr.py:run_tesseract()` (line 140-152)
   - **Current:** Uses `settings.OCR_LANG` globally, fallback logic exists but Urdu not available

6. **Validators for CNIC/Dates/Names**
   - ✅ **Status:** Validators exist
   - **Present:**
     - `validate_cnic()` (validates Pakistan CNIC format)
     - `is_probably_name_line()` (name validation)
   - **Gaps:**
     - ❌ Date validators (Pakistan date formats: DD/MM/YYYY, DD-MM-YYYY)
     - ❌ Urdu name validation (character set checks)
     - **Location:** `backend/app/services/extractors/validators.py`

### Missing for Party Role Extraction:

1. **New Extractors for Seller/Buyer/Witness**
   - ❌ **Status:** Not implemented
   - **Gap:** Need extractors that look for context around sale deed patterns:
     - "Seller:", "Buyer:", "Witness:", "Vendor:", "Purchaser:", etc.
     - Urdu equivalents: "فروخت کنندہ", "خریدار", "گواہ"
   - **Location:** New file: `backend/app/services/extractors/party_roles.py`

2. **Field Key Registration**
   - ⚠️ **Status:** Field keys are string-based, no central registry
   - **Gap:** Need to add extraction logic in `autofill_dossier()` for:
     - `party.seller.names`
     - `party.buyer.names`
     - `party.witness.names`
   - **Location:** `backend/app/services/dossier_autofill.py` (after line 475, where `party.name.raw` is extracted)

3. **Validator Registration**
   - ✅ **Status:** Pattern-based registration works
   - **Note:** `get_field_validator()` will automatically use `is_probably_name_line` for any field with 'name' in the key
   - **Gap:** May need Urdu-specific name validation if names contain Urdu script

---

## D) IMPLEMENTATION PLAN

### Phase 1: Urdu OCR Infrastructure

#### Step 1.1: Install Urdu Language Pack
**Files to modify:**
- `backend/Dockerfile` (line 5)
  ```dockerfile
  RUN apt-get update && apt-get install -y \
      curl \
      tesseract-ocr \
      tesseract-ocr-urd \
      poppler-utils \
      ...
  ```
**Dependencies:** None (system package)

#### Step 1.2: Add Image Processing Dependencies
**Files to modify:**
- `backend/pyproject.toml` (add to dependencies)
  ```toml
  "opencv-python-headless",
  "numpy",
  "scikit-image",  # Optional: for advanced denoising
  ```
- `backend/Dockerfile` (line 19-40, add to pip install)
  ```dockerfile
  RUN pip install --no-cache-dir \
      ...
      opencv-python-headless \
      numpy \
      scikit-image \
      ...
  ```

#### Step 1.3: Create Enhanced Preprocessing Module
**New file:** `backend/app/services/ocr_preprocess.py`
- **Functions:**
  - `deskew_image(image: Image.Image) -> Image.Image`
  - `remove_background_shading(image: Image.Image) -> Image.Image`
  - `enhance_contrast(image: Image.Image) -> Image.Image`
  - `crop_margins(image: Image.Image, threshold: float = 0.95) -> Image.Image`
  - `denoise_image(image: Image.Image) -> Image.Image`
  - `preprocess_for_ocr(image: Image.Image, dpi: int = 300) -> Image.Image` (orchestrator)

#### Step 1.4: Create Script Detection Module
**New file:** `backend/app/services/ocr_script_detect.py`
- **Functions:**
  - `detect_script_dominance(image: Image.Image, lang_hint: Optional[str] = None) -> Tuple[str, float]`
    - Returns: `("urd" | "eng" | "mixed", confidence_score)`
  - **Method:** Character frequency analysis or Tesseract language detection API
  - **Alternative:** Use Tesseract's built-in script detection if available

#### Step 1.5: Create Unified OCR Engine Wrapper
**New file:** `backend/app/services/ocr_engine.py`
- **Functions:**
  - `ocr_image_with_lang(image: Image.Image, lang: str = "eng+urd", dpi: int = 300, preprocess: bool = True) -> Tuple[str, Optional[float], dict]`
  - **Logic:**
    1. Optionally detect script and adjust lang
    2. Preprocess image (enhanced pipeline)
    3. Run Tesseract with correct lang
    4. Return text, confidence, metadata

#### Step 1.6: Update OCR Service to Use New Pipeline
**File:** `backend/app/services/ocr.py`
- **Modify:** `run_tesseract()` to call `ocr_engine.ocr_image_with_lang()`
- **Modify:** `pdf_to_image()` to support configurable DPI (300-400 range)
- **Modify:** `preprocess_image()` to call enhanced preprocessing module

#### Step 1.7: Add Configuration Options
**File:** `backend/app/core/config.py`
- Add:
  ```python
  OCR_DPI_MIN: int = 300
  OCR_DPI_MAX: int = 400
  OCR_ENABLE_SCRIPT_DETECTION: bool = True
  OCR_ENABLE_ENHANCED_PREPROCESS: bool = True
  ```

### Phase 2: Party Role Extraction

#### Step 2.1: Create Party Roles Extractor
**New file:** `backend/app/services/extractors/party_roles.py`
- **Functions:**
  - `extract_seller_names(ocr_text: str) -> List[Tuple[str, float, int, int]]`
  - `extract_buyer_names(ocr_text: str) -> List[Tuple[str, float, int, int]]`
  - `extract_witness_names(ocr_text: str) -> List[Tuple[str, float, int, int]]`
- **Patterns:**
  - English: "Seller:", "Vendor:", "Buyer:", "Purchaser:", "Witness:", "Witness 1:", etc.
  - Urdu: "فروخت کنندہ", "خریدار", "گواہ" (requires Urdu OCR)
  - Context-aware: Look for names on lines after these labels
  - Use `extract_name_lines()` for filtering candidate lines

#### Step 2.2: Integrate Party Roles into Autofill
**File:** `backend/app/services/dossier_autofill.py`
- **Import:** Add `from app.services.extractors.party_roles import extract_seller_names, extract_buyer_names, extract_witness_names`
- **Modify:** `autofill_dossier()` function (after line 475, where `party.name.raw` is extracted)
  ```python
  # Extract party roles
  for value, conf, start, end in extract_seller_names(ocr_text):
      field_path = 'party.seller.names'
      # ... append to all_extractions ...
  
  for value, conf, start, end in extract_buyer_names(ocr_text):
      field_path = 'party.buyer.names'
      # ... append to all_extractions ...
  
  for value, conf, start, end in extract_witness_names(ocr_text):
      field_path = 'party.witness.names'
      # ... append to all_extractions ...
  ```

#### Step 2.3: Update Validators (if needed)
**File:** `backend/app/services/extractors/validators.py`
- **Note:** `get_field_validator()` will automatically use `is_probably_name_line` for `party.seller.names`, etc. (because 'name' is in the key)
- **Optional:** Add Urdu-specific name validation if needed
  ```python
  def validate_urdu_name(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
      # Check for Urdu script characters
      # Validate length, token count
      # Return (is_valid, normalized_value, warning)
  ```

#### Step 2.4: Frontend (No changes needed)
- **Status:** `OCRExtractionsPanel` already displays any field_key dynamically
- **Status:** `DossierFieldsEditor` already includes `party.name.seller` in display list (line 32)
- **Note:** Frontend should work automatically once backend creates candidates with new field keys

### Phase 3: Enhanced Validators (Optional Enhancement)

#### Step 3.1: Add Date Validators
**File:** `backend/app/services/extractors/validators.py`
- **Function:** `validate_pakistan_date(s: str) -> Tuple[bool, Optional[str], Optional[str]]`
- **Patterns:** DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
- **Registration:** Update `get_field_validator()` to return date validator for fields containing 'date'

#### Step 3.2: Urdu Name Validation (if needed)
**File:** `backend/app/services/extractors/validators.py`
- **Function:** `validate_urdu_name(s: str) -> Tuple[bool, Optional[str], Optional[str]]`
- **Check:** Urdu script characters (Unicode ranges), length bounds, token count

---

## ORDERED STEPS (Implementation Sequence)

1. **Install Urdu language pack** (Dockerfile)
2. **Add image processing dependencies** (pyproject.toml, Dockerfile)
3. **Create enhanced preprocessing module** (`ocr_preprocess.py`)
4. **Create script detection module** (`ocr_script_detect.py`)
5. **Create unified OCR engine wrapper** (`ocr_engine.py`)
6. **Update OCR service** to use new pipeline (`ocr.py`)
7. **Add configuration options** (`config.py`)
8. **Test Urdu OCR** end-to-end
9. **Create party roles extractor** (`extractors/party_roles.py`)
10. **Integrate party roles into autofill** (`dossier_autofill.py`)
11. **Test party role extraction** end-to-end
12. **Optional: Enhanced validators** (dates, Urdu names)

---

## DEPENDENCIES SUMMARY

### System Packages (Dockerfile):
- `tesseract-ocr-urd` (new)

### Python Packages (pyproject.toml):
- `opencv-python-headless` (new, for advanced preprocessing)
- `numpy` (new, currently optional, should be required)
- `scikit-image` (optional, for advanced denoising)

---

## VERIFICATION COMMANDS

After Step 1.1 (Urdu language pack):
```bash
docker compose exec api tesseract --list-langs
# Expected: eng, osd, urd
```

After Phase 1 (Urdu OCR):
```bash
# Test OCR on Urdu document page
# Verify script detection works
# Verify enhanced preprocessing improves quality
```

After Phase 2 (Party Roles):
```bash
# Run autofill on test case
# Verify party.seller.names, party.buyer.names, party.witness.names candidates created
# Verify UI displays new fields
```

