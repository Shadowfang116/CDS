# Pilot Real Documents Playbook

## Overview

This playbook guides you through testing the platform with real bank diligence documents (scanned PDFs, photos, etc.) to ensure OCR reliability and document review workflows work correctly.

## Prerequisites

1. **Stack is running:** `.\scripts\dev\pilot_reset.ps1` has completed successfully
2. **Test documents ready:**
   - **Demo-safe docs (deterministic):** Use `docs/pilot_samples/` for seeded demo documents
   - **Real docs (local only):** Place your **real PDF, DOCX, or image files** in `docs/pilot_samples_real/` (gitignored)
   - ⚠️ **Important:** You must provide actual PDF/DOCX/image files (not text files)
   - DOCX files are automatically converted to PDF on upload (no manual conversion needed)
   - The script will fail if the document cannot be processed
   - For testing, use a real scanned document, DOCX legal opinion, or photo of a document
3. **No sensitive data:** Use only non-sensitive, anonymized test documents
4. **Folder separation:**
   - `docs/pilot_samples/` - Demo-safe, deterministic documents (committed to repo)
   - `docs/pilot_samples_real/` - Real documents for UAT (gitignored, never committed)
   - `docs/pilot_samples_real_example/` - Safe placeholder PDFs showing structure (committed)

## Quick Start

### Single Document Upload

1. **Upload a real document (PDF or DOCX):**
   ```powershell
   .\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\your_document.pdf"
   # Or DOCX (automatically converted to PDF):
   .\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\legal_opinion.docx"
   ```
   
   **P13:** DOCX files are automatically converted to PDF on upload. The backend handles conversion using LibreOffice - no manual steps required.

2. **Open the case URL** printed by the script

3. **Review in DocumentViewer:**
   - Check OCR status and quality metrics
   - Review OCR text
   - Re-run OCR if needed (force button)

### Multi-Document Case Pilot

For testing complete DHA transfer cases with multiple documents:

1. **Upload multiple documents to a single case (PDF and DOCX supported):**
   ```powershell
   .\scripts\dev\pilot_real_case.ps1 `
     -Title "UBL DHA Transfer Pilot" `
     -Paths @("docs\pilot_samples\Plot No1 Faisal Town.pdf", "docs\pilot_samples\Legal Opinion.docx") `
     -RunRules `
     -GenerateExports
   ```

2. **Expected behavior:**
   - All documents are uploaded and OCR processed
   - Rules are evaluated automatically
   - DHA CPs (DHA-01, DHA-02) will appear if NDC/site plan are missing
   - DHA-03 and DHA-04 CPs will appear if property is constructed and approved_map/completion_certificate are missing
   - Exports are generated (discrepancy letter, bank pack PDF)

3. **Document type inference:**
   - Documents are automatically classified based on filename
   - Look for type badges in DocumentViewer (e.g., "Legal Opinion", "DHA NDC", "Site Plan")
   - Classification happens on upload and is logged in audit events

4. **Review workflow:**
   - Open Documents tab → verify OCR text and document types
   - Check Exceptions/CPs tab → review DHA rules
   - Go to Reports tab → generate/download exports

## Folder Structure

### Demo-Safe Documents (Deterministic)
```
docs/pilot_samples/
├── README.md
├── sample_scanned.pdf (demo document)
└── sample_photo.jpg (optional)
```
These documents are used for deterministic demo scenarios and are committed to the repository.

### Real Documents (Local Only - Gitignored)
```
docs/pilot_samples_real/
├── README.md
├── BANK_CASE__DOC_TYPE__SHORTNAME.pdf (your real PDF documents)
├── BANK_CASE__LEGAL_OPINION__SHORTNAME.docx (your real DOCX documents)
└── ...
```
⚠️ **CRITICAL:** This folder is gitignored. Never commit real bank documents or PII.
**P13:** DOCX files are automatically converted to PDF on upload - no manual conversion needed.

### Example Placeholders (Safe to Commit)
```
docs/pilot_samples_real_example/
├── README.md
├── EXAMPLE_CASE__DHA_NDC__PLACEHOLDER.pdf
├── EXAMPLE_CASE__SALE_DEED__PLACEHOLDER.pdf
├── EXAMPLE_CASE__FARD__PLACEHOLDER.pdf
└── PILOT_DEMO_OPINION.docx (P13: example DOCX)
```
These are synthetic files generated via reportlab/python-docx, safe to commit and demonstrate the expected structure.

## Supported File Types

- **PDF:** Scanned PDFs, text PDFs, multi-page documents
- **DOCX:** Microsoft Word documents (automatically converted to PDF on upload)
- **Images:** PNG, JPG (will be processed as single-page documents)
- **Size limits:** 
  - PDF/Images: Max 50 MB
  - DOCX: Max 25 MB (before conversion)
  - Max pages per document: 50 (configurable via `OCR_MAX_PAGES_PER_DOC`)

## OCR Preset Guidance

The platform uses configurable OCR settings. For best results:

### Clean Text PDF
- **DPI:** 200 (default)
- **Language:** eng (default)
- **PSM:** 6 (default - uniform block of text)
- **Preprocessing:** Optional (may not be needed)

### Scanned Grayscale PDF
- **DPI:** 300 (increase for better quality)
- **Language:** eng
- **PSM:** 6 or 3 (single column)
- **Preprocessing:** Enable (grayscale, contrast, resize)

### Mobile Photo (JPG/PNG)
- **DPI:** 300-400 (higher for photos)
- **Language:** eng
- **PSM:** 6 or 11 (sparse text)
- **Preprocessing:** Enable (essential for photos)

### Configuration

OCR settings are configured via environment variables in `docker-compose.yml` (P8 gold defaults):
- `OCR_DPI=300` - Resolution for OCR (gold default for scanned PDFs)
- `OCR_LANG=eng` - Tesseract language (with graceful Urdu fallback)
- `OCR_PSM=6` - Page segmentation mode
- `OCR_OEM=1` - OCR Engine Mode (LSTM only)
- `OCR_ENABLE_PREPROCESS=true` - Enable image preprocessing (grayscale, contrast, denoise, threshold)
- `OCR_TIMEOUT_SECONDS=120` - Per-page timeout
- `OCR_MAX_PAGES_PER_DOC=50` - Safety limit

**Smart Name Extraction (P8):**
- Party name fields (`party.name.raw`) now filter out narrative sentences
- Only accepts: 2-5 token lines, no digits, no stopwords, no sentence verbs
- Rejects: Long lines (>60 chars), lines with punctuation, narrative text
- Deduplication prevents duplicate candidates

## Step-by-Step Demo Flow

### 1. Upload Real Document

**Option A: Using Script (Recommended)**
```powershell
# PDF:
.\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\sample_scanned.pdf"
# DOCX (automatically converted to PDF):
.\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\legal_opinion.docx"
```

**Option B: Manual Upload via UI**
1. Login as `admin@orga.com`
2. Navigate to a case (or create new)
3. Go to Documents tab
4. Click "Upload Document"
5. Select your PDF, DOCX, or image file
6. Wait for upload to complete (DOCX will be converted automatically)

### 2. Run OCR

**Automatic:** OCR is automatically enqueued after upload.

**Manual (if needed):**
1. In Document Viewer, click "Re-run OCR (force)" button
2. Wait for processing (typically 30-90 seconds per page)

**Monitor Progress:**
- OCR status pill shows: Queued → Processing → Done
- Failed pages are highlighted with error messages
- Average characters per page is displayed

### 3. Review OCR Quality

**In Document Viewer:**
- **OCR Status:** Check the status pill (should be "Done")
- **Quality Metrics:**
  - Avg chars/page: Should be > 100 for meaningful text
  - Failed pages: Should be 0
  - Processing time: Should be < 120s per page
- **OCR Text Panel:** 
  - Expand bottom panel to view extracted text
  - Verify text matches document content
  - Use search/highlight to find keywords

**Common Issues:**
- **Low character count:** Document may be image-heavy or low quality
- **Failed pages:** Check error message, may need preprocessing or higher DPI
- **Timeout:** Large pages or complex layouts may need longer timeout

### 4. Autofill Dossier

**From OCR Text:**
1. Navigate to Dossier tab
2. Click "Run Autofill" button
3. Toggle "Overwrite existing values" if needed (default: OFF)
4. Review extracted fields and confidence scores
5. **Extraction candidates are created** (not directly applied to dossier)
6. Navigate to **OCR Extractions** tab to review and confirm

### 4a. Review OCR Extractions (P8)

**New Workflow:**
1. Navigate to **OCR Extractions** tab
2. View pending extractions with:
   - Field key (e.g., `party.name.raw`)
   - Proposed value (from OCR)
   - Evidence snippet (original OCR line)
   - Confidence score
3. **Edit inline** (if needed):
   - Click in the input field
   - Type corrected value
   - Auto-saves after 800ms
   - "Edited" badge appears if value differs from proposed
4. **Confirm** extraction:
   - Click "Confirm" button
   - Value is written to dossier field
   - Row moves to "Confirmed" tab
   - Evidence (doc/page) is linked
5. **Reject** extraction:
   - Click "Reject" button
   - Provide reason (required)
   - Row moves to "Rejected" tab
6. **Filter by status**: Use pills (All/Pending/Confirmed/Rejected)

**Smart Filtering (P8):**
- Party name fields automatically filter out narrative sentences
- Only clean name lines (2-5 tokens) are proposed
- No duplicates (deduplication by normalized value)

**What Gets Extracted:**
- Plot number, Block, Phase, Scheme name
- District, Tehsil, Mouza
- Khasra numbers
- Registry number and date
- e-Stamp ID/Number

**Evidence:**
- Each autofilled field includes source evidence (document + page + OCR snippet)
- Evidence is automatically linked to the dossier field

### 5. Link Evidence

**To Exceptions:**
1. Navigate to Exceptions tab
2. Click on an exception
3. Click "Attach Evidence"
4. Select document and page number
5. Add optional note

**To Condition Precedents:**
1. Navigate to CPs tab
2. Click on a CP
3. Click "Attach Evidence"
4. Select document and page number

**To Dossier Fields:**
1. Navigate to Dossier tab
2. Find the field
3. Click "Set Source Evidence"
4. Select document and page number

**Attach OCR Snippet (New):**
1. Open DocumentViewer (Documents tab)
2. Select text in OCR Text panel
3. Click "Attach Selected Text" button
4. Choose target: Exception or CP
5. Select the specific exception/CP from dropdown
6. Confirm snippet preview
7. Click "Attach Snippet"
8. Snippet is stored as evidence with document/page reference

### 6. Review Controls & Evidence Checklist (P9)

**On Case Page:**
1. Navigate to the case detail page
2. **Controls & Evidence Checklist** card appears at the top (above tabs)
3. Review the following:

**Regime Inferred:**
- Badge shows detected regime (e.g., "LDA", "DHA", "REVENUE")
- Confidence percentage displayed (e.g., "85%")
- Reasons listed (e.g., "keyword:LDA", "doc_type:lda_*")

**Risk Assessment:**
- Risk badge: Green (low risk), Amber (medium), Red (high)
- Open exception counts by severity (high, medium, low, hard-stop)

**Active Playbooks:**
- List of playbooks applied based on regime
- Each playbook shows ruleset count and hard-stop count
- Example: "LDA / Placement Letter Controls" with 4 rulesets, 3 hard-stops

**Evidence Checklist:**
- Each required evidence item shows:
  - **Code** (e.g., "LDA_APPROVAL")
  - **Label** (e.g., "Approved layout plan / LDA NOC / approval evidence")
  - **Status**: "Provided" (green) or "Missing" (red)
- If **Provided**: Lists matching documents with links
  - Click document name to view in Documents tab
  - Shows document type and page count
- If **Missing**: Shows acceptable document types as badges
  - Example: "lda_layout_plan", "lda_noc", "placement_letter"
  - Helps reviewers know what to upload

**Approval Readiness:**
- **Ready**: Green pill, shows "Ready for approval (no open hard-stops)"
- **Blocked**: Red pill, lists specific blocked reasons:
  - Example: "1 hard-stop exception(s) open: LDA_001"
  - Example: "2 open high-severity exception(s) remaining"
  - Example: "Case status is 'Processing', expected 'Review' or 'Ready for Approval'"

**Actions:**
- **"Go to Documents"** button: Navigate to Documents tab to upload missing evidence
- Uploading a document with matching doc_type automatically flips "Missing" → "Provided"

**What to Show a Bank/Father:**
- **Regime inferred**: Shows which authority/jurisdiction applies (LDA, DHA, Revenue, etc.)
- **Evidence checklist**: Clear list of what's required vs. what's provided
- **Hard-stop reasons**: Explicit blockers preventing approval (e.g., "Missing LDA NOC")
- **How to fix**: Upload documents matching the acceptable doc_type badges
- **Readiness status**: At-a-glance view of whether case can proceed

### 7. Generate Bank Pack

1. Navigate to Reports page
2. Select the case
3. Click "Generate Bank Pack PDF"
4. Wait for generation (typically 5-10 seconds)
5. Download the PDF
6. Verify:
   - **Dossier Summary section** includes autofilled fields with evidence references
   - All citations include document + page references
   - OCR snippets appear in evidence references (if attached)
   - Evidence pages are included in annexures
   - Formatting is consistent

## Troubleshooting

### OCR Failures

**Symptom:** Pages show "Failed" status with error message

**Common Causes:**
1. **File corruption:** Re-upload the document
2. **Unsupported format:** Ensure file is PDF, PNG, or JPG
3. **Timeout:** Large/complex pages may exceed timeout
4. **Memory:** Very large files may cause worker memory issues

**Solutions:**
- Check worker logs: `docker compose logs worker --tail=100`
- Try force re-run: Click "Re-run OCR (force)" button
- Reduce file size or split into smaller documents
- Increase `OCR_TIMEOUT_SECONDS` if needed

### Low OCR Quality

**Symptom:** OCR text is garbled or missing

**Solutions:**
1. **Enable preprocessing:** Set `OCR_ENABLE_PREPROCESS=true`
2. **Increase DPI:** Set `OCR_DPI=300` or higher
3. **Adjust PSM:** Try PSM 3 for single column, PSM 11 for sparse text
4. **Check source quality:** Ensure scanned documents are clear and high resolution

### Upload Failures

**Symptom:** Upload fails with error

**Common Causes:**
1. **File too large:** Exceeds 50 MB limit
2. **Invalid format:** Not PDF, PNG, or JPG
3. **Storage full:** MinIO bucket may be full

**Solutions:**
- Check file size and format
- Verify MinIO is running: `docker compose ps minio`
- Check MinIO logs: `docker compose logs minio`

### Viewer Not Loading

**Symptom:** Document viewer shows blank or error

**Solutions:**
- Check browser console for errors
- Verify document has pages: Check Documents list
- Try refreshing the page
- Check API logs: `docker compose logs api --tail=50`

## OCR Corrections (Overlay) - P14

**When to use:**
- OCR text contains errors (e.g., "Plot No 12" was read as "Plot No 1Z")
- You want to correct the text before running autofill/extractions
- You need to ensure extractions use corrected text

**How to correct OCR:**
1. Open DocumentViewer for the case
2. Navigate to the document and page with the error
3. Click "Edit OCR Text" (Admin/Reviewer only)
4. Edit the text in the textarea
5. Enter a note explaining the correction (required, min 5 chars)
6. Click "Save Correction"

**How it works:**
- Corrections are stored as an overlay (does NOT overwrite raw OCR)
- Raw OCR remains unchanged for audit purposes
- Effective text (used by autofill/extractions) = corrected text if exists, else raw OCR
- You can toggle between Raw/Effective/Corrected views
- You can revert corrections by clicking "Revert to Raw"

**After correction:**
- Click "Re-run Autofill" to regenerate extractions using corrected text
- Navigate to "OCR Extractions" tab to review new candidates
- Confirm extractions to write to dossier

## Dossier Manual Edits (Defensible) - P14

**Requirements:**
- **Note required:** All manual edits must include a note (min 5 characters) explaining why
- **Critical fields require evidence:** The following fields require document/page evidence OR Admin force:
  - `property.plot_number`
  - `property.khasra_numbers`
  - `registration.registry_number`
  - `stamp.estamp_id_or_number`
- **History tracked:** All edits are recorded in field history with timestamp, editor, old→new value, note, and evidence link

**How to edit:**
1. Navigate to case → Dossier tab
2. Find the field you want to edit
3. Click "Edit" button
4. Enter new value
5. Enter note (required)
6. For critical fields: Select document + page as evidence, OR check "Force (no evidence)" if Admin
7. Click "Save"

**Viewing history:**
- Click "History" button next to any field
- See all edits with timestamps, editors, notes, and evidence links
- Click evidence links to navigate to the source document/page

## Best Practices

1. **Test with variety:** Use different document types (scanned PDF, text PDF, DOCX legal opinions, photos)
2. **DOCX conversion:** DOCX files are automatically converted to PDF - verify conversion succeeded by checking document status
3. **OCR corrections:** If OCR text has errors, correct it before running autofill to ensure accurate extractions
4. **Verify OCR quality:** Always check extracted text matches source
5. **Link evidence early:** Attach evidence as you review documents
6. **Monitor processing:** Watch OCR status during processing
7. **Check exports:** Generate bank pack and verify citations are correct
8. **Field validators:** The system automatically filters out invalid extraction candidates (e.g., narrative sentences for name fields). If a candidate doesn't appear, it may have been filtered by validators.

## P13: DOCX Support

**How it works:**
- Drop DOCX files into `docs/pilot_samples_real/` alongside PDFs
- Run `.\scripts\dev\pilot_uat.ps1` - it automatically picks up both PDF and DOCX files
- Backend converts DOCX to PDF using LibreOffice (headless, server-side)
- Conversion is logged in audit events (`document.convert_docx.success` or `.failed`)
- After conversion, DOCX follows the same pipeline as PDF (split pages, OCR, extraction, etc.)

**Size limits:**
- DOCX: Max 25 MB (before conversion)
- PDF/Images: Max 50 MB

**Troubleshooting DOCX conversion:**
- If conversion fails, check API logs: `docker compose logs api --tail=100`
- Verify LibreOffice is installed: `docker compose exec api soffice --version`
- Conversion timeout: 60 seconds (configurable in `doc_convert.py`)

## Expected Timings

- **Upload:** 1-5 seconds (depends on file size)
- **Page splitting:** 2-10 seconds (depends on page count)
- **OCR per page:** 30-90 seconds (depends on complexity)
- **Bank pack generation:** 5-10 seconds

## Next Steps

After verifying real document workflow:
1. Test with multiple document types
2. Verify evidence linking works correctly
3. Generate exports and verify citations
4. Test with edge cases (very large files, poor quality scans)

## Support

If you encounter issues:
1. Check logs: `docker compose logs api worker --tail=200`
2. Verify health: `curl http://localhost:8000/api/v1/health/deep`
3. Review this playbook's troubleshooting section
4. Check demo walkthrough: `docs/08_demo_walkthrough.md`

