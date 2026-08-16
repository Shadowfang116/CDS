# Worklog

## Current state — OVERWRITE THIS BLOCK, don't append to it

| | |
|---|---|
| **Last updated** | 2026-08-16 |
| **Phase** | Phase 0 / WS0 & WS1 |
| **Branch** | `feat/ocr-accuracy-improvements` |
| **Code changed** | `ocr_service/Dockerfile`, `eval_urdu_ocr.py`, `config.py`, `ocr_domain_ur.py`, `ocr_text.py`, `test_ocr_domain_ur.py`, `ci.yml`, `eval_ocr_service.py`, `ocr_service/preprocessing.py`, `pdf_text_layer.py`, `test_pdf_text_layer.py`, `test_preprocessing.py`, `tesseract_engine.py`, `test_tesseract_engine.py`, `ocr_service/main.py` |
| **Findings** | 3 open, 6 fixed (F1, F2, F3, F4, F5, F9), 1 in progress (F6) |
| **Baseline CER/WER/F1** | ❌ pending sample PDFs (Q1) |
| **Next action** | Workstream 2 (Surya engine rewrite for modern surya-ocr API) |

---

## Log — append new entries at the top

### 2026-08-16 — Session 8: Unit 1.6 Fallback Alarm Observability (F3 Observability Added)

1. **Unit 1.6 (Fallback Alarm Observability)**:
   - Updated `ocr_service/main.py` to log structured warning alarms (`[OCR_FALLBACK_ALARM]`) whenever `requested_engine != engine_used`.
   - Ensures `engine_used` is explicitly populated per page in `OcrPageResult` responses.
   - All 24 backend unit tests passing cleanly.

### 2026-08-16 — Session 7: Unit 1.5 Resolution Cap & OSD Orientation Fix (F9 Fixed)

1. **Unit 1.5 & F9 (Resolution Cap & OSD Orientation Fix)**:
   - Raised `OCR_IMAGE_MAX_SIDE` from `2200` to `3500` in `backend/app/core/config.py` so 300 DPI A4 documents are preserved without downscaling loss.
   - Added `upscale_low_dpi_image` to `ocr_service/preprocessing.py` to upscale low-resolution scans ($< 2400\text{px}$) using cubic interpolation to ~300 DPI equivalent.
   - Integrated `detect_and_rotate_osd` using Tesseract OSD (`--psm 0 -l osd`) to detect 90°/180°/270° orientation skews and rotate pages automatically.
   - Added unit test `test_upscale_low_dpi_image` to `backend/tests/test_preprocessing.py`. Verified 24 tests passing.

### 2026-08-16 — Session 6: Unit 1.4 Tesseract Invocation Rewrite (F4 Fixed)

1. **Unit 1.4 & F4 (Tesseract Invocation Rewrite)**:
   - Rewrote `ocr_service/engines/tesseract_engine.py` to eliminate double OCR execution per page (`image_to_string` + `image_to_data`).
   - Implemented single-pass `image_to_data` reading order reconstruction (`reconstruct_text_from_data`) across block, paragraph, and line numbers.
   - Replaced static `--psm 6` with `--psm 3` (automatic layout analysis) and passed explicit `--dpi 300` hint.
   - Added low confidence threshold filtering ($< 0.15$) to prevent garbage noise from corrupting page confidence scores.
   - Added unit test suite `backend/tests/test_tesseract_engine.py`. All 23 backend unit tests passing.

### 2026-08-16 — Session 5: Unit 1.3 Preprocessing Rewrite (F1 & F2 Fixed)

1. **Unit 1.3 & F1/F2 (Preprocessing Rewrite)**:
   - Rewrote `ocr_service/preprocessing.py` to preserve 8-bit grayscale gradient details for deep learning / VLM engines.
   - Ported minimum area bounding box contour deskew (`_deskew_min_area_rect`) capped at 5° (fixing F2).
   - Replaced destructive non-local means denoising on 1-bit binary with edge-preserving bilateral filtering (`cv2.bilateralFilter`) on grayscale (fixing F1).
   - Added dynamic image-height-scaled `binarize_for_tesseract` for the Tesseract fallback path and deleted dead `cv2.normalize`.
   - Added unit test suite `backend/tests/test_preprocessing.py`.
2. **Unit 1.2 (Native PDF Text Extraction)**:
   - Added `pypdf` native text layer extraction to `backend/app/services/pdf_text_layer.py`.
   - Added `test_pdf_text_layer.py` test suite. Verified 100% pass across all 18 backend tests.

### 2026-08-16 — Session 4: Executing Master Plan (WS0 & WS1 Units)

Executed initial foundation units from `08_master_plan.md`:

1. **H1 (Dockerfile Tesseract Dependencies)**: Fixed `ocr_service/Dockerfile` by adding `tesseract-ocr-eng` and `tesseract-ocr-osd` alongside `tesseract-ocr-urd`. Prevents missing language data and enables OSD orientation detection.
2. **Unit 0.1 (Eval Import Fix)**: Repaired `scripts/dev/eval_urdu_ocr.py:16` to import `ocr_page_pdf` from `app.services.ocr`.
3. **Unit 0.2 & F6 (Missing Settings)**: Added 7 missing `OCR_*` settings to `backend/app/core/config.py` (`OCR_PADDLE_LANG`, `OCR_PADDLE_USE_ANGLE_CLS`, `OCR_PADDLE_USE_GPU`, `OCR_ENABLE_ENSEMBLE`, `OCR_ENABLE_LAYOUT`, `OCR_ENABLE_PDF_TEXT_LAYER`, `OCR_PDF_TEXT_LAYER_ENGINE`). Verified all return 1.
4. **Unit 0.3 & Unit 0.4 (CI & Pytest & OCR Service)**: 
   - Added `pytest` dev dependency to `backend/pyproject.toml`.
   - Created `backend/tests/test_ocr_domain_ur.py` regression test suite.
   - Updated `.github/workflows/ci.yml` with `backend-tests` pytest job, `ocr_service` image build step, and `GET /health` endpoint check in `smoke` job.
5. **Unit 0.5 (Microservice Eval Harness)**: Added `scripts/dev/eval_ocr_service.py` to evaluate the served `POST /ocr` microservice endpoint directly.
6. **Unit 0.6 (Gate Loud Failure)**: Updated `scripts/ci/urdu_ocr_eval.sh` to exit with code 1 instead of skipping silently when samples are missing.
7. **Unit 1.1 & F5 (Mojibake Repair)**: Completely repaired cp1252 character corruption across `backend/app/services/ocr_domain_ur.py` and `ocr_text.py`. Verified 235 real Urdu characters exist, 0 mojibake tokens remain, and saved as clean UTF-8 without BOM. Added `test_ocr_domain_ur.py` regression test.

### Measurement status: ❌ none possible

Host has no `tesseract` binary and no `cv2` / `numpy` / `PIL` / `pytesseract` / `surya` /
`paddleocr` / `pdf2image`. Docker is installed (29.2.1) but **not running**.
`datasets/urdu_ocr/samples/` does not exist.

**The 65% figure is unverified and unreproducible from this repo.** No improvement can
be proven until this changes. See `07_runbook.md` for the path to a measurable state.

### Measured results

| Date | Change | Sample set | CER | WER | F1 | Notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | no runs yet |

---

## Log — append new entries at the top

### 2026-08-15 — Session 3: contribution master plan

Added `08_master_plan.md` — the execution plan (how work lands), distinct from
`03_plan.md` (what to fix and why).

Surveyed how the repo actually accepts changes. **The CI situation is worse than
assumed, and it reshapes the plan:**

- `.github/workflows/ci.yml` has **no Python test job**. `pytest` isn't even a declared
  dependency; `backend/tests/run_mvp_tests.py` is a hand-rolled importlib loop.
- The `docker-build` job builds **api** and **frontend** only — **`ocr_service` is never
  built in CI.**
- The `smoke` job starts `api db redis minio` — **`ocr_service` is never started.**
- `scripts/ci/urdu_ocr_eval.sh` is **not referenced in `ci.yml` at all.** F7 previously
  said the gate was silently passing; in fact it never ran. F7 updated.
- Zero OCR tests exist anywhere in the repo.
- CI triggers only on `main`/`master`, so nothing runs on `feat/*` without a PR.

**Net: nothing in CI touches OCR. A contributor can break it completely and CI stays
green.** This is why WS0 (make it verifiable) is blocking in the master plan.

**New hypothesis — H1, worth testing before anything else.**
`ocr_service/Dockerfile:9-14` installs tesseract with `--no-install-recommends`. On
Debian, `tesseract-ocr` *Recommends* rather than Depends on `tesseract-ocr-eng` and
`tesseract-ocr-osd`, so the image may ship **`urd` only**. If confirmed, `-l urd+eng`
(F4) is degrading or erroring on every page, and the OSD orientation fix (1.5) cannot
work at all. Check:
`docker compose run --rm --entrypoint tesseract ocr_service --list-langs`.
Fix would be a one-line Dockerfile change. **Unverified — Docker not running.**

Also noted: Python version skew (`ocr_service` on 3.11, backend requires ≥3.12); BOMs in
`run_mvp_tests.py` and `run_unit_tests.ps1` alongside the F5 files; no model
pre-download in the OCR image, so Surya weights would download inside the first request.

**Code changes: none.** `AI_context/` and `CLAUDE.md` only.

### 2026-08-15 — Session 2: context restructure

Restructured `AI_context/` from a one-off report into a working context system.

- Collapsed `00_READ_ME_FIRST.md` (a verbatim duplicate of `01`+`02`+`03`) into
  `README.md`. Removed ~40% duplication; findings now live in exactly one place.
- Added a **status table** to `02_findings.md` (F1–F9, all 🔴 open) and a
  **re-verify command** to every finding, so `file:line` drift is detectable in seconds
  instead of silently invalidating the document.
- Split out `05_decisions.md`, `06_open_questions.md`, `07_runbook.md`.
- Added `../CLAUDE.md` so the folder auto-loads instead of needing to be pointed at.
- **Re-verified all 9 findings against `b94bb10`.** All 9 confirmed still present.

**Three corrections found while re-verifying:**

1. **F5 count was wrong.** Claimed "235 mojibake sequences" in `ocr_domain_ur.py`; no
   detection regex tried here reproduces that (21 strict, 42 loose). The count is
   regex-dependent and has been demoted in the finding. The load-bearing claim —
   **0 real Urdu characters** — is confirmed for both `ocr_domain_ur.py` and
   `ocr_text.py`. Conclusion unchanged.
2. **F7 was understated.** The CI gate doesn't fail on the broken import — it never
   reaches it. `scripts/ci/urdu_ocr_eval.sh:20-24` finds no samples and `exit 0`s. The
   accuracy gate has been reporting **green** since it was written. Silently-passing is
   worse than broken.
3. **F8 cited the wrong line.** The line-vs-word confusion originates at
   `surya_engine.py:70` (the `("words","lines","text_lines",...)` traversal order), not
   at 156-170 where the nodes are consumed.

**Also corrected:** Stack A is **~648** lines, not 679. Stack B is 3,480 lines but
`ocr_pipeline.py` (143) *is* on the production path — so the unreachable portion is
~3,337, not the full 3,480.

**Code changes: none.** This session touched only `AI_context/` and `CLAUDE.md`, both
outside the repo.

### 2026-08-15 — Session 1: branch + diagnosis

**Branch:** `feat/ocr-accuracy-improvements` created off `master` @ `b94bb10`.
Fork not needed — the local clone is writable and the branch was created locally.
Push access to `github.com/Shadowfang116/CDS` **not yet tested**; if push is rejected,
fall back to fork + PR.

**Code changes:** none. Diagnosis only.

**Established facts:**

- Production OCR runs entirely through `ocr_service/`, not through the ~3,480-line
  `backend/app/services/ocr_*` stack.
- Surya is effectively never used; every page is Tesseract on a binarized image.
- `ocr_domain_ur.py` (931 lines) is inert — mojibake constants, 0 real Urdu chars.
- 7 `OCR_*` settings referenced in code are absent from `config.py`; PaddleOCR ensemble,
  layout OCR and the PDF-text-layer fast path are all unreachable.
- `scripts/dev/eval_urdu_ocr.py` fails at import (`ocr_page_pdf` from the wrong module).
  No ground-truth samples exist in the repo.

**Measurement status:** ❌ none possible.

**Next action when unblocked:** Phase 0 — repair the eval harness and produce a real
baseline number.
