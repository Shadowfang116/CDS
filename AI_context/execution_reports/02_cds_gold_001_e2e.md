# CDS-GOLD-001 end-to-end run — 2026-08-17

**Case:** `4673c7f2-5f39-4ebb-8f4a-4406fab0decc`  
**UI:** http://localhost:3000/dashboard/cases/4673c7f2-5f39-4ebb-8f4a-4406fab0decc  
**Corpus:** `C:\Users\fahad\Downloads\CDS_GOLD_001_URDU_PDF_CORPUS`  
**Login:** `admin@orga.com`  
**OCR engine used:** Tesseract (`surya` requested, fallback alarm fired on every page)

Raw snapshots: `cds_gold_001_e2e_initial.json`, `cds_gold_001_e2e_final.json`.

## What ran

1. Rebuilt API (contextual autofill). Set worker `RULEPACK_PATH=/app/docs/05_rulepack_v1.yaml` (worker was looking at `/docs/...` and failing `run_rules` after OCR).
2. Created a fresh matter. Uploaded all **11** initial PDFs. OCR completed (sale deed 5 pages, others 2–3). Quality recorded as Good.
3. Autofill `overwrite=true`. Evaluated rules.
4. Uploaded all **5** additional PDFs. OCR completed. Autofill overwrite again. Evaluated rules.

All **16** corpus PDFs are on the matter.

## Autofill vs gold truth (names / property)

Gold matter: borrower `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ`, plot 82, Industrial Block-B.

| Field | Gold | After initial autofill | After additional overwrite |
|---|---|---|---|
| `property.plot_number` | 82 | **82** (0.95) | **82** (0.95) |
| `property.block` | B | **B** (0.95) | **B** (0.95) |
| `party.seller.names` | محمد اکرم | **محمد اکرم** (`clause_urdu`, sale deed) | **رجسٹریشن حوالہ** (mutation labelled form) |
| `party.buyer.names` | اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ | **match** (`clause_urdu`, sale deed) | **/ منتقل الیہ** (mutation) |
| `party.witness.names` | none / placeholders | `سب رجسٹرار` (anchor, 0.45, needs_review) | `سب رجسٹرار` |

Initial autofill is the F10 win. The second overwrite is a regression: mutation is routed as a party-role doc, and a weak `clause_urdu` hit on form labels beat the sale-deed names in the persisted candidate row (one Pending row per field_key).

Dossier currently stores `property.plot_number=82`, `property.block=B`, `property.regime=SOCIETY`. Party names were **not** confirmed into the dossier.

## Exceptions vs gold_truth.yaml

Gold wants seven **content** defects (area 4 Kanal vs 3 Kanal 18 Marla, missing building plan, development charges, prior charge, stale fard, name variant, historic PT-10). The live rulepack fired **generic missing-document** rules instead.

| Gold ID | Expected | Initial | After additional evidence |
|---|---|---|---|
| GOLD-EX-001 area mismatch | open → resolved by corrected fard | **not raised** | **not raised** |
| GOLD-EX-002 building plan missing | open → resolved | Low “Missing Approved Building Plan” | **dropped** (plan PDF present) |
| GOLD-EX-003 development charges | open → resolved | not as gold (generic “Outstanding Society Dues”) | still Open |
| GOLD-EX-004 prior charge | open → resolved | “Prior Encumbrance Indicator” Open | still Open (release letter not accepted) |
| GOLD-EX-005 stale fard | open → resolved | **not raised** | **not raised** |
| GOLD-EX-006 name variant | open → resolved | **not raised** | **not raised** |
| GOLD-EX-007 historic tax waiver | open → waived | **not raised** | **not raised** |

Decision stayed **FAIL** (24 then 25 exceptions, 5 hard stops). Additional evidence did **not** close the gold set. False positives remain, e.g. “Missing Possession Documentation” and “Missing Registered Title Instrument” despite `09_Possession_Letter_URDU.pdf` and `01_Registered_Sale_Deed_URDU.pdf` — likely `doc_type` not inferred on upload.

## Pipeline notes

- Cookie login is `/api/v1/auth/login` (dev-login is gone). `pilot_real_case.ps1` still calls dev-login.
- Worker without `RULEPACK_PATH` marks the OCR Celery task failed after pages are already `Done`. Page OCR is fine; auto `run_rules` from the worker is not. API `/evaluate` is the path that actually scored the matter.
- Autofill wait: sale-deed OCR ~30s; additional batch ~3 minutes.

## Next product gaps this run proved

1. Prefer sale-deed `clause_urdu` over later mutation labelled hits; do not let overwrite replace a higher-quality party candidate with a worse one.
2. Tighten mutation routing / refuse `منتقل الیہ` and `رجسٹریشن حوالہ` as names.
3. Gold defects (area, stale fard, name variant) are not in the current rulepack.
4. Infer `doc_type` from these filenames so missing-instrument rules do not fire on documents that are present.
