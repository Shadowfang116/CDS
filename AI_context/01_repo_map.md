# Repo map — where OCR lives

Verified against `CDS` @ **`b94bb10`**. Line counts are a snapshot and will drift —
regenerate rather than trusting them:

```bash
find ocr_service -name '*.py' | xargs wc -l | sort -n
ls backend/app/services/ocr*.py | xargs wc -l | sort -n
```

---

## Two separate OCR stacks exist. Only the weaker one runs.

### Stack A — `ocr_service/` microservice (THIS IS WHAT RUNS IN PRODUCTION)

```
ocr_service/
├── main.py             197   FastAPI /ocr endpoint, page fan-out, engine resolution
├── preprocessing.py     60   grayscale → adaptive threshold → deskew → denoise
├── quality.py           79   heuristic quality score (word count / chars-per-word)
├── schemas.py           31   OcrRequest / OcrPageResult / WordBox
└── engines/
    ├── surya_engine.py 188   calls surya.ocr.run_ocr(...)
    └── tesseract_engine.py 92  pytesseract, "--oem 1 --psm 6 -l urd+eng"
```

**~648 lines total.** No DPI handling, no orientation detection, no script detection,
no ensemble, no post-correction.

Deployed as its own compose service (`docker-compose.yml:70-84`), port 8001,
`OCR_ENGINE` defaults to `surya` — which never actually loads (F3).

### Stack B — `backend/app/services/ocr_*.py` (WRITTEN, ALMOST ENTIRELY UNREACHABLE)

```
ocr.py                233   page → image → OCR entrypoint (ocr_page_pdf)
ocr_engine.py         243   script-aware lang selection, OSD, dynamic DPI
ocr_preprocess.py     257   crop margins, background removal, CLAHE, bilateral,
                            minAreaRect deskew  ← the correct deskew lives here
ocr_script_detect.py  159   Urdu vs English dominance + rotation
ocr_paddle.py         132   PaddleOCR wrapper for ensemble
ocr_layout.py         362   layout segmentation OCR
ocr_fallback.py       236   low-confidence retry path
ocr_text.py           236   text cleanup
ocr_text_quality.py   281   mojibake detection/repair, corruption checks
ocr_domain_ur.py      931   Urdu legal/property normalization (CNIC, dates, khasra, areas)
ocr_eval.py           257   CER / WER / F1 scoring
ocr_quality.py         10   thin shim
ocr_pipeline.py       143   ← EXCEPTION: this one DOES run. HTTP client to Stack A.
```

**~3,480 lines total**, of which only `ocr_pipeline.py` (143) is on the production
path — and it contains no OCR logic, only the HTTP call to Stack A.

So: **~3,337 lines of OCR capability that never executes.** See `02_findings.md`.

## Actual production request path

```
POST /documents/{id}/ocr
  └─ Celery: app/workers/tasks_ocr.py :: process_document_ocr
       ├─ _render_page_asset_to_base64_png()
       │    └─ _render_page_pdf_to_base64_png() → ocr.pdf_to_image()
       │         └─ ocr_engine.pdf_to_image_dynamic(max_side=OCR_IMAGE_MAX_SIDE)
       │              ← downscales to 2200 px here (F9)
       └─ app/services/ocr_pipeline.py :: run_ocr_pipeline()
            └─ HTTP POST {OCR_SERVICE_URL}/ocr    ← leaves the backend entirely
                 │  (page as base64 PNG inside a JSON body)
                 └─ ocr_service/main.py :: _process_page_sync()
                      ├─ preprocessing.preprocess_page()   ← binarizes the page (F1/F2)
                      ├─ engines.surya_engine.run_surya()  ← fails (F3)
                      └─ engines.tesseract_engine.run_tesseract()  ← produces the text (F4)
       └─ writes page.ocr_text / ocr_confidence / ocr_quality_signal
```

`tasks_ocr.py:17` imports `run_ocr_pipeline`; `run_ocr_pipeline` only speaks HTTP to
the microservice (`ocr_pipeline.py:89`, `OCR_SERVICE_URL`).
**No OCR logic from Stack B is on this path.**

The two Stack-B OCR modules reachable from anywhere at all:
- `ocr_engine.ocr_image` ← called by `ocr.py:221` (inside `ocr_page_pdf`, which the
  Celery path never calls)
- `ocr_fallback.get_page_text_with_fallback` ← called by `dossier_autofill.py:596`
  (autofill only, *after* OCR has already been persisted)

**Practical consequence:** any fix must land in `ocr_service/`, or be ported there.
Improving Stack B changes nothing in production. This is the single most important
fact in this folder.

## Eval tooling

```
datasets/urdu_ocr/README.md                well-written spec for a golden dataset
                                           (targets: CER ≤ 0.28 scanned, ≤ 0.10 native)
datasets/urdu_ocr/manifests/manifest.json  1 item, "sample1", 2 pages — files absent
datasets/urdu_ocr/samples/                 DOES NOT EXIST (gitignored, never populated)
scripts/dev/eval_urdu_ocr.py         424   the runner — broken import (F7)
scripts/ci/urdu_ocr_eval.sh                CI wrapper — exits 0 when samples missing (F7)
backend/app/services/ocr_eval.py     257   CER/WER/F1 implementation (this part is fine)
```

Note the eval targets **Stack B** (`ocr_page_pdf`), not the microservice. Even repaired,
it would measure code that does not serve traffic. Phase 0 adds a `POST /ocr` eval.

## Related services

`hf-extractor` (`docker-compose.yml:45`) is a separate extraction service — not part of
the OCR path. Autofill may call it text-only, capped at 3 pages, for CNIC/plot/scheme
labels. It is not the party-role path. Flagged so it isn't mistaken for OCR.

## Post-OCR autofill (field extraction)

This runs **after** page OCR is persisted. It does not replace `ocr_service/`.

```
dossier_autofill.autofill_dossier
  ├─ get_page_text_with_fallback (persisted OCR ± corrections)
  ├─ doc_routing.classify_document  → sale_deed | tax | cnic | …
  ├─ sale_deed_clauses.extract_sale_deed_clauses  (seller/buyer/witness)
  ├─ party_roles.extract_party_roles_from_document (fallback, no overwrite of clause hits)
  ├─ regex plot/block/registry (Urdu + English)
  ├─ candidate_gate + validators (refuse watermarks / boilerplate)
  └─ ocr_extraction_candidates (Pending)
        └─ confirm → case_dossier_fields
```

Party roles only on sale_deed / mutation. Plot/block may corroborate across tax,
valuation, possession. Confirm is still required for the dossier (D7).
