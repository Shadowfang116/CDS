-- SQL Queries for Prompt 5/12 E2E Verification Proof
-- Replace <CASE_ID>, <SALE_DEED_DOC_ID>, <FARD_DOC_ID> with actual IDs from test output

-- Query A — Party role rows (expected: 3 rows total for sale deed, 0 for Fard)
-- Proves: Party role candidates exist only for sale deed document
SELECT
  oec.field_key,
  oec.document_id,
  d.original_filename AS document_name,
  oec.page_number,
  oec.confidence,
  oec.proposed_value
FROM ocr_extraction_candidates oec
JOIN documents d ON d.id = oec.document_id
WHERE oec.case_id = '<CASE_ID>'
  AND oec.field_key IN ('party.seller.names','party.buyer.names','party.witness.names')
ORDER BY d.original_filename, oec.field_key, oec.created_at DESC;

-- Query B — Duplicate detector (expected: 0 rows)
-- Proves: No duplicates exist per (document_id, field_key)
SELECT
  oec.document_id,
  d.original_filename AS document_name,
  oec.field_key,
  COUNT(*) AS row_count
FROM ocr_extraction_candidates oec
JOIN documents d ON d.id = oec.document_id
WHERE oec.case_id = '<CASE_ID>'
  AND oec.field_key IN ('party.seller.names','party.buyer.names','party.witness.names')
GROUP BY oec.document_id, d.original_filename, oec.field_key
HAVING COUNT(*) > 1
ORDER BY row_count DESC;

-- Query C — Candidate confidence range check (expected: 0 rows)
-- Proves: Candidate confidence is within [0,1]
SELECT id, field_key, confidence
FROM ocr_extraction_candidates
WHERE case_id = '<CASE_ID>'
  AND confidence IS NOT NULL
  AND (confidence < 0 OR confidence > 1);

-- Query D — Page confidence range check (expected: 0 rows)
-- Proves: Page ocr_confidence is within [0,1]
SELECT document_id, page_number, ocr_confidence
FROM document_pages
WHERE document_id IN ('<SALE_DEED_DOC_ID>', '<FARD_DOC_ID>')
  AND ocr_confidence IS NOT NULL
  AND (ocr_confidence < 0 OR ocr_confidence > 1)
ORDER BY document_id, page_number;

-- Query E — Any party candidates regardless of key spelling (expected: shows party.* if written)
SELECT field_key, document_id, COUNT(*) 
FROM ocr_extraction_candidates
WHERE case_id = '<CASE_ID>'
  AND field_key LIKE 'party.%'
GROUP BY field_key, document_id
ORDER BY field_key, document_id;

-- Query F — Latest 30 candidates (sanity)
SELECT created_at, field_key, document_id, confidence, LEFT(proposed_value,120) AS v
FROM ocr_extraction_candidates
WHERE case_id = '<CASE_ID>'
ORDER BY created_at DESC
LIMIT 30;

-- Query G — HF Extractor CNIC candidates (expected: >0 rows for sale_deed.pdf with CNIC entities)
-- Proves: HF extractor entities are persisted with evidence_json
SELECT
  oec.field_key,
  oec.document_id,
  d.original_filename AS document_name,
  oec.page_number,
  oec.confidence,
  oec.proposed_value,
  oec.extraction_method,
  oec.evidence_json
FROM ocr_extraction_candidates oec
JOIN documents d ON d.id = oec.document_id
WHERE oec.case_id = '<CASE_ID>'
  AND oec.extraction_method = 'hf_extractor'
  AND d.original_filename LIKE '%sale_deed%'
ORDER BY d.original_filename, oec.page_number, oec.created_at DESC;

-- Query H — All HF Extractor candidates grouped by field_key and page_number
-- Proves: All entity types (CNIC, PLOT_NO, SCHEME_NAME, etc.) are extracted and persisted
SELECT
  oec.field_key,
  oec.document_id,
  d.original_filename AS document_name,
  oec.page_number,
  oec.confidence,
  oec.proposed_value,
  oec.extraction_method,
  oec.evidence_json->>'label' AS entity_label,
  oec.evidence_json->>'ocr_engine' AS ocr_engine,
  COUNT(*) OVER (PARTITION BY oec.field_key, oec.page_number) AS count_per_field_page
FROM ocr_extraction_candidates oec
JOIN documents d ON d.id = oec.document_id
WHERE oec.case_id = '<CASE_ID>'
  AND oec.extraction_method = 'hf_extractor'
ORDER BY oec.field_key, oec.page_number, oec.created_at DESC;

-- Query I — LayoutXLM candidates with evidence JSON fields (Prompt 11)
-- Purpose: Verify evidence JSON consistency for layoutxlm-v1 extraction
-- Shows: raw_value, normalized_value, extractor_version_used, model_name_or_path, OCR metadata, low_confidence
SELECT
  oec.field_key,
  oec.proposed_value,
  oec.extraction_method,
  oec.confidence,
  oec.page_number,
  oec.evidence_json->>'raw_value' AS raw_value,
  oec.evidence_json->>'normalized_value' AS normalized_value,
  oec.evidence_json->>'extractor_version_used' AS extractor_version_used,
  oec.evidence_json->>'model_name_or_path' AS model_name_or_path,
  oec.evidence_json->>'label' AS label,
  oec.evidence_json->>'low_confidence' AS low_confidence,
  oec.evidence_json->>'ocr_page_confidence' AS ocr_page_confidence,
  oec.evidence_json->>'ocr_used_fallback' AS ocr_used_fallback,
  oec.created_at
FROM ocr_extraction_candidates oec
WHERE oec.case_id = '<CASE_ID>'::uuid
  AND oec.document_id = '<DOCUMENT_ID>'::uuid
  AND oec.extraction_method = 'hf_extractor'
  AND oec.evidence_json->>'extractor_version_used' = 'layoutxlm-v1'
ORDER BY oec.page_number, oec.field_key, oec.created_at DESC
LIMIT 50;

-- Query J — Party roles for THIS RUN ONLY (P20)
-- Purpose: Verify deterministic per-run tracking - shows only party roles from the current autofill run
-- Expected: Exactly 3 rows (seller, buyer, witness) for the given run_id
-- Replace <CASE_ID>, <SALE_DEED_DOC_ID>, <RUN_ID> with actual values
SELECT 
  field_key, 
  document_id, 
  page_number, 
  confidence, 
  proposed_value, 
  run_id
FROM ocr_extraction_candidates
WHERE case_id = '<CASE_ID>'::uuid
  AND document_id = '<SALE_DEED_DOC_ID>'::uuid
  AND field_key IN ('party.seller.names','party.buyer.names','party.witness.names')
  AND run_id = '<RUN_ID>'
ORDER BY field_key;

-- Query K — Party names must not contain newlines or leading/trailing whitespace (run-scoped) (P23)
-- Purpose: Regression check - ensures party role values are properly normalized
-- Expected: 0 rows (all party names should be clean)
-- Replace <RUN_ID> with actual run_id
SELECT field_key, proposed_value
FROM ocr_extraction_candidates
WHERE run_id = '<RUN_ID>'
  AND field_key LIKE 'party.%'
  AND (
    proposed_value LIKE E'%\n%'
    OR proposed_value LIKE E'%\r%'
    OR proposed_value ~ '(^\\s|\\s$)'
  );
