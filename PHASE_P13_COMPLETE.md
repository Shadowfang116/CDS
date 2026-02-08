# Phase P13/12 COMPLETE — DOCX Ingest + Real-Doc Folder Runner

## Summary

Phase P13 delivers end-to-end DOCX support with automatic server-side conversion to PDF, enabling seamless ingestion of legal opinion documents alongside PDFs in the pilot workflow.

## Backend Implementation

### 1. LibreOffice Integration
**File:** `backend/Dockerfile`
- Added `libreoffice-writer` and `libreoffice-core` to API container
- Conversion runs server-side (no host dependencies)

### 2. DOCX Conversion Service
**File:** `backend/app/services/doc_convert.py` (NEW)
- Function: `convert_docx_bytes_to_pdf(docx_bytes, filename, timeout_seconds=60)`
- Uses LibreOffice headless: `soffice --headless --convert-to pdf`
- Enforces 60-second timeout
- Validates PDF output (non-empty, valid PDF header)
- Comprehensive error handling with bank-safe messages
- Automatic temp file cleanup

### 3. Document Model Enhancement
**File:** `backend/app/models/document.py`
- Added `meta_json` JSONB column to store conversion metadata
- Migration: `backend/alembic/versions/p13_add_document_metadata_json.py`

### 4. Upload Endpoint Integration
**File:** `backend/app/api/routes/documents.py`
- Added DOCX content type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Content type inference from file extension if missing
- DOCX size limit: 25 MB (before conversion)
- Automatic conversion on upload (before PDF split pipeline)
- Metadata stored in `meta_json`:
  - `source_format: "docx"`
  - `original_mime_type`
  - `conversion` object with processing time, sizes, converter name

### 5. Audit Logging
**Events added:**
- `document.convert_docx.success` - Includes processing_seconds, sizes
- `document.convert_docx.failed` - Includes sanitized reason
- `document.upload` - Now includes `original_mime_type` and `converted_from` if applicable

## Scripts Updated

### 1. `scripts/dev/pilot_real_doc.ps1`
- Accepts `.docx` files
- DOCX size limit: 25 MB (vs 50 MB for PDF/images)
- Content type detection for DOCX
- No manual conversion needed

### 2. `scripts/dev/pilot_real_case.ps1`
- Accepts `.docx` in `-Paths` array
- Validates DOCX size (25 MB limit)
- Uploads DOCX files seamlessly alongside PDFs

### 3. `scripts/dev/pilot_uat.ps1`
- Scans `docs/pilot_samples_real/` for both `.pdf` and `.docx` files
- Reports counts: "X PDF(s), Y DOCX file(s)"
- Processes all documents automatically

## Testing

### 1. Example DOCX File
**File:** `docs/pilot_samples_real_example/PILOT_DEMO_OPINION.docx`
- Generated via `scripts/dev/generate_example_pdfs.py` (updated to support DOCX)
- Contains realistic property/registry fields for extraction testing
- Safe to commit (no PII)

### 2. Smoke Test
**File:** `scripts/dev/smoke_test.ps1`
- **Test 29:** "P13: DOCX upload converts to PDF and OCR completes"
- Flow:
  - Creates test case
  - Uploads example DOCX
  - Asserts document created with page_count >= 1
  - Asserts content_type is "application/pdf" (after conversion)
  - Enqueues OCR and waits for completion
  - Verifies done_count == total_pages
- No skips - fails with clear message if LibreOffice missing

## Documentation

### Updated `docs/09_pilot_real_docs_playbook.md`
- Added DOCX to supported file types
- Updated Quick Start with DOCX examples
- Added "P13: DOCX Support" section with:
  - How it works
  - Size limits
  - Troubleshooting guide
- Updated folder structure to show DOCX examples

## Key Features

1. **Zero Manual Conversion:** DOCX → PDF happens automatically on upload
2. **Deterministic:** Same pipeline as PDF (split, OCR, extraction, exports)
3. **Tenant-Isolated:** All conversions respect org_id
4. **Auditable:** Conversion events logged with metadata
5. **Safe:** Timeouts, size limits, error handling, temp file cleanup
6. **No Regression:** Existing PDF flow unchanged

## Verification Steps

1. **Build and start:**
   ```powershell
   docker compose up -d --build
   ```

2. **Run migrations:**
   ```powershell
   docker compose exec api alembic upgrade head
   ```

3. **Generate example DOCX:**
   ```powershell
   docker compose exec api python scripts/dev/generate_example_pdfs.py
   ```

4. **Test DOCX upload:**
   ```powershell
   .\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples_real_example\PILOT_DEMO_OPINION.docx"
   ```

5. **Run smoke tests:**
   ```powershell
   .\scripts\dev\smoke_test.ps1
   ```
   - Test 29 should pass (DOCX upload and OCR)

6. **Run UAT with mixed files:**
   - Place PDFs and DOCX files in `docs/pilot_samples_real/`
   - Run: `.\scripts\dev\pilot_uat.ps1`
   - Verify all files processed

## Acceptance Criteria Met

✅ **A) Backend DOCX → PDF conversion:**
- LibreOffice installed in API container
- Conversion service with timeout and validation
- Wired into upload endpoint
- Audit logging for success/failure
- Security constraints (size limits, temp cleanup)

✅ **B) Scripts accept PDF + DOCX:**
- `pilot_real_doc.ps1` accepts DOCX
- `pilot_real_case.ps1` accepts DOCX
- `pilot_uat.ps1` scans for both PDF and DOCX

✅ **C) Testing:**
- Example DOCX file created
- Smoke test for DOCX upload and OCR completion
- No skips - clear failure if LibreOffice missing

✅ **D) Acceptance criteria:**
- Docker compose builds successfully
- DOCX upload produces pages and thumbnails
- OCR runs on converted PDF
- UAT runner processes PDF + DOCX mix
- Tenant isolation intact
- Audit log includes conversion events

## Known Limitations

1. **DOCX size limit:** 25 MB (vs 50 MB for PDF) - conversion overhead
2. **Conversion timeout:** 60 seconds - may need adjustment for very large/complex DOCX
3. **LibreOffice dependency:** Requires LibreOffice in container (adds ~200MB to image)

## Next Steps

1. Test with real legal opinion DOCX files
2. Monitor conversion performance in production
3. Adjust timeout if needed for large documents
4. Consider adding support for other Office formats (XLSX, PPTX) if needed

---

**Phase P13 Status:** ✅ COMPLETE

**Date:** 2025-01-15

**Ready for:** Pilot testing with real DOCX legal opinions

