-- Prompt 16: SQL Debug Helper for Party Roles Page Text Verification
-- Replace <CASE_ID>, <SALE_DEED_DOC_ID>, <FARD_DOC_ID> with actual IDs

-- Query 1: Per-page OCR engine and text quality for sale deed document
-- Shows which pages were repaired/re-OCRed (indicated by engine containing "+repaired" or "urd_fallback")
-- Purpose: Verify page texts are fixed (post-fallback values are used)
SELECT
    dp.document_id,
    d.original_filename AS document_name,
    dp.page_number,
    dp.ocr_engine,
    dp.ocr_confidence,
    CASE 
        WHEN dp.ocr_engine LIKE '%repaired%' THEN 'REPAIRED'
        WHEN dp.ocr_engine LIKE '%urd_fallback%' OR dp.ocr_engine LIKE '%urd+eng%' THEN 'RE_OCRED'
        ELSE 'ORIGINAL'
    END AS ocr_status,
    LENGTH(dp.ocr_text) AS text_length,
    LEFT(dp.ocr_text, 80) AS ocr_text_preview
FROM document_pages dp
JOIN documents d ON d.id = dp.document_id
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
ORDER BY dp.page_number;

-- Query 2: Count mojibake-detected pages (if any flag stored)
-- Note: We don't currently store a mojibake flag, but we can infer from ocr_engine
-- If ocr_engine contains "+repaired" or "urd_fallback", the page was likely corrupted
SELECT
    d.original_filename AS document_name,
    COUNT(*) FILTER (WHERE dp.ocr_engine LIKE '%repaired%') AS pages_repaired,
    COUNT(*) FILTER (WHERE dp.ocr_engine LIKE '%urd_fallback%' OR dp.ocr_engine LIKE '%urd+eng%') AS pages_re_ocred,
    COUNT(*) FILTER (WHERE dp.ocr_engine NOT LIKE '%repaired%' AND dp.ocr_engine NOT LIKE '%urd_fallback%' AND dp.ocr_engine NOT LIKE '%urd+eng%') AS pages_original,
    COUNT(*) AS total_pages
FROM document_pages dp
JOIN documents d ON d.id = dp.document_id
WHERE dp.document_id IN ('<SALE_DEED_DOC_ID>', '<FARD_DOC_ID>')
  AND dp.ocr_text IS NOT NULL
GROUP BY d.id, d.original_filename
ORDER BY d.original_filename;

-- Query 3: Check for mojibake characters in page text (detection)
-- Shows pages that contain known mojibake characters
SELECT
    dp.document_id,
    d.original_filename AS document_name,
    dp.page_number,
    dp.ocr_engine,
    (
        SELECT COUNT(*)
        FROM unnest(string_to_array(dp.ocr_text, NULL)) AS chars
        WHERE chars IN ('╪', '┘', '┌', '▒', '█', '▓', '⌐', 'º', '┤', 'ü', '¿', '»',
                        '║', '╔', '╗', '╚', '╝', '═', '╬', '╩', '╦', '╠', '╣', '╤', '╧', '╥', '╨')
    ) AS mojibake_char_count,
    LEFT(dp.ocr_text, 100) AS ocr_text_preview
FROM document_pages dp
JOIN documents d ON d.id = dp.document_id
WHERE dp.document_id = '<SALE_DEED_DOC_ID>'
  AND dp.ocr_text IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM unnest(string_to_array(dp.ocr_text, NULL)) AS chars
      WHERE chars IN ('╪', '┘', '┌', '▒', '█', '▓', '⌐', 'º', '┤', 'ü', '¿', '»',
                      '║', '╔', '╗', '╚', '╝', '═', '╬', '╩', '╦', '╠', '╣', '╤', '╧', '╥', '╨')
  )
ORDER BY dp.page_number;

-- Query 4: Sale deed detection keywords check (for both sale deed and Fard)
-- Verifies which documents are detected as sale deeds
SELECT
    d.id,
    d.original_filename,
    CASE WHEN EXISTS (
        SELECT 1 FROM document_pages dp 
        WHERE dp.document_id = d.id 
        AND (
            dp.ocr_text ILIKE '%sale deed%' OR dp.ocr_text ILIKE '%deed of sale%'
            OR dp.ocr_text ILIKE '%vendor%' OR dp.ocr_text ILIKE '%vendee%'
            OR dp.ocr_text ILIKE '%seller%' OR dp.ocr_text ILIKE '%buyer%'
        )
    ) THEN TRUE ELSE FALSE END AS has_sale_deed_en,
    CASE WHEN EXISTS (
        SELECT 1 FROM document_pages dp 
        WHERE dp.document_id = d.id 
        AND (
            dp.ocr_text LIKE '%بیع نامہ%' OR dp.ocr_text LIKE '%فروخت نامہ%' 
            OR dp.ocr_text LIKE '%فروخت کنندہ%' OR dp.ocr_text LIKE '%خریدار%'
            OR dp.ocr_text LIKE '%گواہ%'
        )
    ) THEN TRUE ELSE FALSE END AS has_sale_deed_urdu,
    COUNT(DISTINCT dp.id) AS page_count
FROM documents d
LEFT JOIN document_pages dp ON dp.document_id = d.id AND dp.ocr_text IS NOT NULL
WHERE d.case_id = '<CASE_ID>'
  AND d.id IN ('<SALE_DEED_DOC_ID>', '<FARD_DOC_ID>')
GROUP BY d.id, d.original_filename
ORDER BY d.original_filename;

-- Query 5: Party role candidates check (Query A equivalent)
-- Expected: 3 rows for sale_deed.pdf, 0 rows for Fard
SELECT
    oec.field_key,
    oec.document_id,
    d.original_filename AS document_name,
    oec.page_number,
    oec.confidence,
    LEFT(oec.proposed_value, 100) AS proposed_value_preview,
    oec.extraction_method,
    oec.created_at
FROM ocr_extraction_candidates oec
JOIN documents d ON d.id = oec.document_id
WHERE oec.case_id = '<CASE_ID>'
  AND oec.field_key IN ('party.seller.names','party.buyer.names','party.witness.names')
ORDER BY d.original_filename, oec.field_key, oec.created_at DESC;
