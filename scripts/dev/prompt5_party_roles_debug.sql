-- SQL Debug Queries for Party Role Extraction
-- Replace <CASE_ID>, <SALE_DEED_DOC_ID>, <FARD_DOC_ID> with actual IDs

-- Query A: Per-page anchor presence for sale deed
-- Shows which pages contain Urdu/English anchors and preview of OCR text
SELECT 
    dp.page_number,
    CASE WHEN dp.ocr_text ILIKE '%فریق%' OR dp.ocr_text ILIKE '%فریق اول%' OR dp.ocr_text ILIKE '%فریق دوم%' 
              OR dp.ocr_text ILIKE '%فروخت%' OR dp.ocr_text ILIKE '%خریدار%' OR dp.ocr_text ILIKE '%گواہ%' 
              OR dp.ocr_text ILIKE '%گواہان%' OR dp.ocr_text ILIKE '%شاہد%' THEN TRUE ELSE FALSE END AS has_urdu_anchor,
    CASE WHEN dp.ocr_text ILIKE '%vendor%' OR dp.ocr_text ILIKE '%vendee%' OR dp.ocr_text ILIKE '%seller%' 
              OR dp.ocr_text ILIKE '%buyer%' OR dp.ocr_text ILIKE '%purchaser%' OR dp.ocr_text ILIKE '%witness%' 
              OR dp.ocr_text ILIKE '%first party%' OR dp.ocr_text ILIKE '%second party%' THEN TRUE ELSE FALSE END AS has_english_anchor,
    LEFT(dp.ocr_text, 250) AS ocr_preview
FROM document_pages dp
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
ORDER BY dp.page_number;

-- Query B: CNIC pattern presence per page
-- Counts CNIC-like patterns (hyphenated and non-hyphenated)
SELECT 
    dp.page_number,
    (LENGTH(dp.ocr_text) - LENGTH(REPLACE(dp.ocr_text, '#####-#######-#', ''))) / LENGTH('#####-#######-#') AS hyphenated_cnic_count,
    (LENGTH(dp.ocr_text) - LENGTH(REPLACE(REGEXP_REPLACE(dp.ocr_text, '[^0-9]', '', 'g'), '0000000000000', ''))) / 13 AS digit_sequence_count,
    COUNT(*) FILTER (WHERE dp.ocr_text ~ '\d{5}[- ]?\d{7}[- ]?\d') AS cnic_like_patterns
FROM document_pages dp
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
GROUP BY dp.page_number, dp.ocr_text
ORDER BY dp.page_number;

-- Query C: Dump suspect lines containing party role tokens or CNIC patterns
-- Returns lines that might contain party role information
SELECT 
    dp.page_number,
    dp.ocr_text AS full_page_text,
    unnest(string_to_array(dp.ocr_text, E'\n')) AS line_text
FROM document_pages dp
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
  AND (
    -- Urdu tokens
    dp.ocr_text ILIKE '%فریق%' OR dp.ocr_text ILIKE '%فریق اول%' OR dp.ocr_text ILIKE '%فریق دوم%'
    OR dp.ocr_text ILIKE '%فروخت%' OR dp.ocr_text ILIKE '%خریدار%' OR dp.ocr_text ILIKE '%گواہ%'
    OR dp.ocr_text ILIKE '%گواہان%' OR dp.ocr_text ILIKE '%شاہد%'
    -- English tokens
    OR dp.ocr_text ILIKE '%vendor%' OR dp.ocr_text ILIKE '%vendee%' OR dp.ocr_text ILIKE '%seller%'
    OR dp.ocr_text ILIKE '%buyer%' OR dp.ocr_text ILIKE '%purchaser%' OR dp.ocr_text ILIKE '%witness%'
    -- CNIC patterns
    OR dp.ocr_text ~ '\d{5}[- ]?\d{7}[- ]?\d' OR dp.ocr_text ~ '\d{13}'
  )
ORDER BY dp.page_number;

-- Query D: CNIC token extraction (detailed)
-- Shows actual CNIC-like tokens found per page
SELECT 
    dp.page_number,
    regexp_matches(dp.ocr_text, '\d{5}[- ]?\d{7}[- ]?\d', 'g') AS cnic_hyphenated,
    regexp_matches(dp.ocr_text, '\d{13}', 'g') AS cnic_digits_only
FROM document_pages dp
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
  AND (dp.ocr_text ~ '\d{5}[- ]?\d{7}[- ]?\d' OR dp.ocr_text ~ '\d{13}')
ORDER BY dp.page_number;

-- Query E: Sale deed detection keywords check
-- Verifies which sale deed keywords are present
SELECT 
    d.id,
    d.original_filename,
    CASE WHEN EXISTS (
        SELECT 1 FROM document_pages dp 
        WHERE dp.document_id = d.id 
        AND dp.ocr_text ILIKE '%sale deed%' OR dp.ocr_text ILIKE '%deed of sale%'
    ) THEN TRUE ELSE FALSE END AS has_sale_deed_en,
    CASE WHEN EXISTS (
        SELECT 1 FROM document_pages dp 
        WHERE dp.document_id = d.id 
        AND (dp.ocr_text LIKE '%بیع نامہ%' OR dp.ocr_text LIKE '%فروخت نامہ%' OR dp.ocr_text LIKE '%فروخت کنندہ%')
    ) THEN TRUE ELSE FALSE END AS has_sale_deed_urdu
FROM documents d
WHERE d.case_id = '<CASE_ID>'
ORDER BY d.created_at;

