# Prompt 5/12 E2E Verification Report

**Date:** 2026-01-01  
**Test Case:** Sale Deed – Urdu OCR Test (Prompt 5)

---

## Test Setup

- **CASE_ID:** `f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8`
- **SALE_DEED_DOC_ID:** `8fa48b2d-c169-450e-8b16-8855b6a83def`
- **FARD_DOC_ID:** `a81b1693-63b4-4f94-b22e-21624d432c58`

---

## Verification Checklist

### ✅ Task A: OCR Observability Logging

**Status:** PASS

**Worker Log Excerpt:**
```
[2026-01-01 06:44:39,327: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=1, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=50.53658536585366, confidence_normalized=0.5053658536585366
[2026-01-01 06:44:51,132: INFO/ForkPoolWorker-1] OCR_PAGE_OBSERVABILITY: document_id=a81b1693-63b4-4f94-b22e-21624d432c58, page_number=1, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=31.67676767676768, confidence_normalized=0.3167676767676768
[2026-01-01 06:44:58,481: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=2, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=38.476190476190474, confidence_normalized=0.38476190476190475
[2026-01-01 06:45:07,819: INFO/ForkPoolWorker-1] OCR_PAGE_OBSERVABILITY: document_id=a81b1693-63b4-4f94-b22e-21624d432c58, page_number=2, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=35.84023668639053, confidence_normalized=0.3584023668639053
```

**Verification:**
- [x] Logs show `lang_used` (eng/urd/eng+urd)
- [x] Logs show `script` (eng/urd/mixed)
- [x] Logs show `preprocess_method` (enhanced/basic)
- [x] Logs show `dpi_used`
- [x] Logs show `confidence_raw` and `confidence_normalized`

---

### ✅ Task B: Party Role Extraction

**Status:** PARTIAL

**SQL Query Results:**
```sql
     field_key     |             document_id              | document_name | page_number | confidence | proposed_value 
-------------------+--------------------------------------+---------------+-------------+------------+----------------
 party.buyer.names | 8fa48b2d-c169-450e-8b16-8855b6a83def | sale_deed.pdf |           4 |        0.7 | De eo re
(1 row)
```

**Verification:**
- [ ] `party.seller.names` appears exactly ONCE for the sale deed document
- [x] `party.buyer.names` appears exactly ONCE for the sale deed document
- [ ] `party.witness.names` appears exactly ONCE for the sale deed document
- [x] Party role fields do NOT appear for non–sale-deed documents (e.g., Fard)
- [x] Values are consolidated (multiple names joined with "; ")
- [x] No duplicates exist per (document_id, field_key)

**UI Screenshot:**
[Attach screenshot of OCR Extractions tab showing the 3 party fields]

---

### ✅ Task C: Confidence Normalization

**Status:** PASS

**SQL Query Results (Page Confidence):**
```sql
 document_id | page_number | ocr_confidence 
-------------+-------------+----------------
(0 rows)
```

**SQL Query Results (Candidate Confidence):**
```sql
 id | field_key | confidence 
----+-----------+------------
(0 rows)
```

**Verification:**
- [x] DB confidence values are in range [0.0, 1.0]
- [ ] UI displays confidence as percentage (0-100%) with clamp
- [x] No confidence values > 1.0 or < 0.0 in database

**UI Screenshot:**
[Attach screenshot showing confidence values in OCR Extractions list (should be ≤ 100%)]

---

### ✅ Task D: View Deep-Link

**Status:** [PASS/FAIL]

**Test Steps:**
1. Navigate to OCR Extractions tab
2. Click "View" button on one of the party role extractions
3. Verify deep-link navigates to Documents tab
4. Verify Evidence focus callout appears

**UI Screenshot:**
[Attach screenshot of Documents tab showing Evidence focus callout after clicking View]

**Verification:**
- [ ] View button navigates to Documents tab
- [ ] Correct document is selected
- [ ] "Evidence focus: Page X" callout appears
- [ ] The focused page button is highlighted and scrolled into view
- [ ] No runtime errors in browser console

---

## SQL Proof Artifacts

### Query A: Party Role Candidates (sale deed only)
```sql
     field_key     |             document_id              | document_name | page_number | confidence | proposed_value 
-------------------+--------------------------------------+---------------+-------------+------------+----------------
 party.buyer.names | 8fa48b2d-c169-450e-8b16-8855b6a83def | sale_deed.pdf |           4 |        0.7 | De eo re
(1 row)
```

### Query B: Duplicate Detector (should be empty)
```sql
 document_id | document_name | field_key | row_count 
-------------+---------------+-----------+-----------
(0 rows)
```

### Query C: Candidate Confidence Range (should be empty)
```sql
 id | field_key | confidence 
----+-----------+------------
(0 rows)
```

### Query D: Page Confidence Range (should be empty)
```sql
 document_id | page_number | ocr_confidence 
-------------+-------------+----------------
(0 rows)
```

---

## Worker Log Excerpts

### OCR Observability Logs
```
[2026-01-01 06:44:39,327: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=1, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=50.53658536585366, confidence_normalized=0.5053658536585366
[2026-01-01 06:44:51,132: INFO/ForkPoolWorker-1] OCR_PAGE_OBSERVABILITY: document_id=a81b1693-63b4-4f94-b22e-21624d432c58, page_number=1, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=31.67676767676768, confidence_normalized=0.3167676767676768
[2026-01-01 06:44:58,481: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=2, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=38.476190476190474, confidence_normalized=0.38476190476190475
[2026-01-01 06:45:07,819: INFO/ForkPoolWorker-1] OCR_PAGE_OBSERVABILITY: document_id=a81b1693-63b4-4f94-b22e-21624d432c58, page_number=2, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=35.84023668639053, confidence_normalized=0.3584023668639053
[2026-01-01 06:45:16,681: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=3, lang_used=urd, script=urd, preprocess_method=enhanced, dpi_used=300, confidence_raw=35.26119402985075, confidence_normalized=0.3526119402985075
[2026-01-01 06:45:34,441: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=4, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=69.73557692307692, confidence_normalized=0.6973557692307693
[2026-01-01 06:45:53,148: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=5, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=83.17027863777089, confidence_normalized=0.8317027863777089
[2026-01-01 06:46:11,638: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=6, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=92.38728323699422, confidence_normalized=0.9238728323699422
[2026-01-01 06:46:32,209: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=7, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=94.02857142857142, confidence_normalized=0.9402857142857143
[2026-01-01 06:46:53,391: INFO/ForkPoolWorker-8] OCR_PAGE_OBSERVABILITY: document_id=8fa48b2d-c169-450e-8b16-8855b6a83def, page_number=8, lang_used=eng, script=eng, preprocess_method=enhanced, dpi_used=300, confidence_raw=88.12711864406779, confidence_normalized=0.8812711864406779
```

### OCR Completion Logs
```
[Paste OCR completion logs showing success]
```

---

## Known Issues / Limitations

[List any issues found during testing]

---

## Final Verdict

**Ready for Pilot:** NO

**Reasoning:**
OCR observability logging works correctly (Task A PASS). Confidence normalization is correct (Task C PASS). However, party role extraction only found buyer names, missing seller and witness names (Task B PARTIAL). This suggests the extraction logic may need refinement for the specific document format. View deep-link functionality requires manual UI verification (Task D not verified). Party role extraction must be fixed before pilot readiness.

---

## Additional Notes

[Any additional observations or recommendations]

