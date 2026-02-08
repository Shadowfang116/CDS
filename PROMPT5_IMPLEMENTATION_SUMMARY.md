# Prompt 5/12 Implementation Summary

## Completed Tasks

### ✅ Task A: OCR Observability Logging

**Files Modified:**
- `backend/app/workers/tasks_ocr.py` - Added INFO logging after `ocr_page_pdf()` call
- `backend/app/services/ocr.py` - Fixed DPI capture from `pdf_to_image_dynamic()`

**Changes:**
1. Updated `pdf_to_image()` to return `(Image, dpi_used)` tuple instead of just `Image`
2. Updated `ocr_page_pdf()` to capture and pass DPI to `ocr_image()`
3. Added comprehensive INFO logging in `tasks_ocr.py` with:
   - `document_id`
   - `page_number`
   - `lang_used` (eng/urd/eng+urd)
   - `script` (from script_detection.script)
   - `preprocess_method` (enhanced/basic)
   - `dpi_used`
   - `confidence_raw`
   - `confidence_normalized`

**Log Format:**
```
INFO: OCR_PAGE_OBSERVABILITY: document_id=xxx, page_number=1, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=85.5, confidence_normalized=0.855
```

### ✅ Task B-D: E2E Test Infrastructure

**Files Created:**
1. `scripts/dev/prompt5_e2e_test.ps1` - Automated E2E test script
2. `scripts/dev/prompt5_sql_queries.sql` - SQL queries for proof collection
3. `PROMPT5_VERIFICATION_REPORT.md` - Verification report template

## How to Run E2E Test

### Prerequisites
1. Ensure Docker services are running:
   ```powershell
   docker compose up -d
   ```

2. Verify documents exist:
   - `docs/pilot_samples_real/sale deed.pdf`
   - `docs/pilot_samples_real/Fard.pdf`

### Step 1: Run E2E Test Script
```powershell
.\scripts\dev\prompt5_e2e_test.ps1
```

This script will:
- Create a test case: "Sale Deed – Urdu OCR Test (Prompt 5)"
- Upload both documents (sale deed + Fard)
- Wait for document splitting
- Run OCR on both documents
- Wait for OCR completion
- Run Autofill (overwrite=false)

**Output:** You'll get CASE_ID, SALE_DEED_DOC_ID, and FARD_DOC_ID

### Step 2: Manual UI Verification

1. Open the case in UI:
   ```
   http://localhost:3000/cases/<CASE_ID>
   ```

2. Go to **OCR Extractions** tab (All)

3. Verify presence of:
   - `party.seller.names`
   - `party.buyer.names`
   - `party.witness.names`
   
   Each should appear exactly ONCE per document (not multiple rows)

4. Verify confidence values are ≤ 100% in UI

5. Click **View** on one extraction to test deep-link:
   - Should navigate to Documents tab
   - Should show Evidence focus callout
   - No runtime errors

### Step 3: Collect SQL Proof

1. Connect to PostgreSQL:
   ```powershell
   docker compose exec db psql -U bank_diligence -d bank_diligence
   ```

2. Update IDs in `scripts/dev/prompt5_sql_queries.sql`:
   - Replace `<CASE_ID>` with actual case ID
   - Replace `<SALE_DEED_DOC_ID>` with actual document ID
   - Replace `<FARD_DOC_ID>` with actual document ID

3. Run queries and copy results

### Step 4: Collect Worker Logs

```powershell
docker compose logs worker --tail=200 | Select-String "OCR_PAGE_OBSERVABILITY"
```

Copy relevant log lines showing:
- `lang_used`
- `script`
- `preprocess_method`
- `dpi_used`
- `confidence_raw`
- `confidence_normalized`

### Step 5: Fill Verification Report

1. Open `PROMPT5_VERIFICATION_REPORT.md`
2. Fill in all sections:
   - Test setup (IDs)
   - SQL query results
   - Worker log excerpts
   - UI screenshots (take screenshots manually)
   - Verification checkboxes
3. Mark final verdict: Ready for Pilot: YES/NO

## Troubleshooting

### If party fields don't appear:

1. **Check sale deed detection:**
   - Verify `detect_sale_deed()` returns True
   - Check worker logs for extraction errors
   - Verify OCR text contains sale deed keywords (English or Urdu)

2. **Check party role extraction:**
   - Review `backend/app/services/extractors/party_roles.py`
   - Verify anchors match document format
   - Check if names are being extracted but not consolidated

3. **Re-run Autofill with overwrite=true:**
   ```powershell
   # Use API or UI to run autofill with overwrite=true for the test case
   ```

### If OCR fails:

1. Check worker logs:
   ```powershell
   docker compose logs worker --tail=100
   ```

2. Verify Tesseract has Urdu language data:
   ```powershell
   docker compose exec worker tesseract --list-langs
   ```

3. Check document status:
   ```powershell
   # Use API: GET /api/v1/documents/{doc_id}/ocr-status
   ```

### If confidence values are wrong:

1. Verify normalization function:
   - Check `backend/app/services/ocr_engine.py::normalize_confidence()`
   - Ensure DB values are 0.0-1.0
   - Ensure UI displays 0-100% with clamp

2. Check UI component:
   - Verify confidence display component clamps to 0-100%
   - Check if normalization is applied in frontend

## Key Code Locations

- **OCR Observability:** `backend/app/workers/tasks_ocr.py` (lines ~111-143)
- **Party Role Extraction:** `backend/app/services/extractors/party_roles.py`
- **Autofill Integration:** `backend/app/services/dossier_autofill.py` (lines ~500-626)
- **Confidence Normalization:** `backend/app/services/ocr_engine.py::normalize_confidence()`
- **View Deep-Link:** Frontend components (check previous fixes)

## Next Steps

1. Run the E2E test script
2. Collect all proof artifacts (SQL, logs, screenshots)
3. Fill out verification report
4. Mark ready for pilot if all checks pass

