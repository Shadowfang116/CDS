# Phase P14/12 Progress — Real-Doc Extraction QA

## Backend Implementation (COMPLETE)

### ✅ A) OCR Text Corrections
1. **Model:** `backend/app/models/ocr_text_correction.py` - Created
2. **Migration:** `backend/alembic/versions/p14_ocr_text_corrections.py` - Created
3. **API Routes:** `backend/app/api/routes/ocr_text_corrections.py` - Created
   - PUT `/documents/{doc_id}/pages/{page}/ocr-text/correction` - Upsert correction
   - DELETE `/documents/{doc_id}/pages/{page}/ocr-text/correction` - Delete correction
4. **Updated:** `backend/app/api/routes/documents_phase10.py`
   - GET `/documents/{doc_id}/pages/{page}/ocr-text` - Now supports `?mode=effective|raw|corrected`
   - Returns corrected text, note, corrected_by, corrected_at
5. **Integration:** `backend/app/services/dossier_autofill.py`
   - Uses corrected OCR text when available (effective text)
   - Evidence snippets reference effective text

### ✅ B) Field Validators
1. **Validators Service:** `backend/app/services/extractors/validators.py` - Created
   - `is_probably_name_line()` - Rejects narrative sentences
   - `validate_cnic()` - Pakistan CNIC format
   - `validate_plot()` - Plot number normalization
   - `validate_khasra_list()` - Khasra list format
   - `validate_registry_number()` - Registry number format
   - `validate_estamp()` - E-stamp ID format
   - `generic_sentence_rejector()` - Fallback narrative rejector
2. **Autofill Integration:** `backend/app/services/dossier_autofill.py`
   - Validates field values before creating candidates
   - Invalid values are skipped (zero garbage)
   - Validated/normalized values stored in candidates
   - Warning reasons combined with quality warnings

### ✅ C) Dossier Field Edit Tightening
1. **Updated:** `backend/app/api/routes/dossier_fields.py`
   - PATCH requires `note` (min 5 chars)
   - Critical fields require evidence OR `force=true` (Admin only)
   - Critical fields: `property.plot_number`, `property.khasra_numbers`, `registration.registry_number`, `stamp.estamp_id_or_number`
   - Audit events: `dossier.field_edit_force_no_evidence` when force used

### ✅ D) OCR Extraction Confirm Validation
1. **Updated:** `backend/app/api/routes/ocr_extractions.py`
   - Confirm endpoint validates field format using validators
   - Invalid format returns 400 unless `force_format=true` (Admin only)
   - Audit event: `ocr.extraction_force_format` when force_format used

## Frontend Implementation (IN PROGRESS)

### ✅ API Client Updates
1. **Updated:** `frontend/lib/api.ts`
   - Added `getDossierFields()`, `patchDossierField()`, `getDossierFieldHistory()`, `linkDossierFieldEvidence()`
   - Added `getOcrText()`, `putOcrTextCorrection()`, `deleteOcrTextCorrection()`
   - Updated `confirmOCRExtraction()` to support `forceFormat` parameter

### ⏳ Remaining Frontend Work
1. **DossierFieldsEditor Component** - Needs creation
2. **DocumentViewer OCR Correction Overlay** - Needs update
3. **Case Page Integration** - Wire DossierFieldsEditor into dossier tab

## Testing (PENDING)

### ⏳ Smoke Tests
1. OCR correction overlay test
2. Critical dossier edit requires evidence test
3. Validator blocks narrative test
4. Audit events verification test

## Documentation (PENDING)

### ⏳ Update Playbook
- Add OCR Corrections section
- Add Field Validators section

---

**Status:** Backend complete, frontend in progress, tests pending

**Next Steps:**
1. Complete DocumentViewer OCR correction UI
2. Create DossierFieldsEditor component
3. Add smoke tests
4. Update documentation

