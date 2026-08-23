# Plan — raising OCR accuracy

This is the canonical statement of the accuracy target and the work sequence.
Findings referenced as F1–F9 are defined in `02_findings.md`.

## First, on the "99%" target

The target needs to be split, because one number is hiding three very different problems.

| Metric | Realistic ceiling on this document mix | Notes |
|---|---|---|
| **Native-text PDFs** (embedded text layer) | **99%+** | Achievable and easy — stop rasterizing them. Pure routing fix (F6). |
| **Printed / typed English + Urdu Nastaleeq scans, char accuracy (1−CER)** | **92-97%** | With a modern DL engine (Surya/PaddleOCR), correct preprocessing and correct DPI. |
| **Handwritten or degraded Urdu Nastaliq scans, char accuracy** | **70-85%** | State-of-the-art. No pipeline reaches 99% here. |
| **Field-level accuracy on the fields that matter** (CNIC, khasra/khewat, dates, amounts, names) | **99% achievable** | Not via raw OCR — via checksum/format validation, domain lexicons, cross-page agreement, and routing anything unvalidated to human review. |

**Recommendation:** target **99% on validated key fields** (with a measured auto-accept
rate), and **best-effort maximum on raw CER**. Committing to "99% raw CER on scanned
Urdu" would be committing to something no OCR system currently delivers.

The repo's own `datasets/urdu_ocr/README.md` already sets a sane bar: CER ≤ 0.28 for
scanned Urdu, ≤ 0.10 for native text. Those are reasonable Phase-1 exit criteria.

This framing is **not yet agreed** — see Q3 in `06_open_questions.md`. Record the
answer in `05_decisions.md` when it lands.

---

## Phase 0 — Make accuracy measurable (blocking prerequisite)

Nothing else can be claimed without this. The eval harness doesn't import, the CI gate
silently passes, and there is no ground truth (F7).

1. Fix `scripts/dev/eval_urdu_ocr.py:16` import (`ocr_page_pdf` is in `app.services.ocr`).
2. Add the missing settings to `config.py` so the gated code paths are reachable (F6).
3. **Add a microservice-level eval that hits `POST /ocr` directly**, so the thing that
   actually runs in production is the thing being measured. Without this, the eval
   measures Stack B — i.e. dead code.
4. Make `scripts/ci/urdu_ocr_eval.sh` **fail loudly** when samples are missing, instead
   of `exit 0`. A skipped gate must not look like a passing one.
5. Populate `datasets/urdu_ocr/samples/` with ~20-30 representative pages + ground truth.
   **Needs the user — see Q1 in `06_open_questions.md`.**
6. Baseline run → record the real current CER/WER/F1 in `04_worklog.md`. Confirm or
   correct the "65%".

**Deliverable:** a single command producing per-page and aggregate CER/WER/F1.
**Exit criterion:** a baseline number exists in the worklog, reproducible twice.

## Phase 1 — Stop the bleeding (highest impact per line changed)

Ordered by expected gain. Every item lands in `ocr_service/` — see `01_repo_map.md`
for why Stack B changes don't count.

1. **Route native-text PDFs around OCR entirely** (F6). Wire `pdf_text_layer.py` in,
   gate on extracted-char-count + garbage ratio, fall back to OCR when the layer is
   empty or garbage. Instant ~100% on that slice.
   *Blast radius: small — additive fast path with a fallback.*
2. **Rewrite `ocr_service/preprocessing.py`** (F1, F2):
   - keep a **grayscale** (not binarized) image as the default engine input;
   - produce a binarized variant *only* for the Tesseract path;
   - replace the moment-based deskew with the `minAreaRect` implementation that already
     exists and is correct at `backend/app/services/ocr_preprocess.py:146`;
   - drop `fastNlMeansDenoising` on binary; use a bilateral filter on grayscale;
   - scale `blockSize` with estimated text height instead of hard-coding 31;
   - delete the no-op `cv2.normalize`.
   *Blast radius: medium — this is the single function every page passes through.
   Do it after Phase 0, never before.*
3. **Fix the Tesseract call** (F4): single `image_to_data` pass with reading-order
   reconstruction, `--psm 3/4` chosen per page, `--dpi` passed explicitly, confidence
   floor on kept words.
   *Blast radius: small — one function, contained.*
4. **Fix DPI and orientation** (F9):
   - raise `OCR_IMAGE_MAX_SIDE` from 2200 to ≥ 3500 so 300 DPI A4 survives;
   - upscale low-DPI input to a ~300 DPI equivalent before OCR;
   - add OSD rotation correction to the microservice.
   *Blast radius: small.*
5. **Stop shipping page images as base64-in-JSON** (F9) — multipart, or a shared object
   store reference. This is what makes the 2200 px cap feel necessary.
   *Blast radius: **large** — changes the contract between Celery worker and the
   microservice. Split into its own change, after 4 is measured. Do not bundle.*

## Phase 2 — Get a real engine running

6. **Rewrite `surya_engine.py` against the current surya API** (F3):
   `DetectionPredictor` + `RecognitionPredictor` (+ `FoundationPredictor` on recent
   versions), models loaded once at FastAPI startup, batched across pages.
   **Pin `surya-ocr` to an exact version** in `ocr_service/requirements.txt`.
7. **Add PaddleOCR as a second engine** and wire the ensemble that `ocr_paddle.py` was
   written for — add the missing settings, add `paddleocr` to the service requirements,
   pick the winner per page/line by confidence + script-consistency.
8. **Fail loudly instead of silently degrading.** Right now a dead engine looks like a
   working one — `OCR_ENGINE` says `surya`, Tesseract does the work, nothing reports it.
   Surface `engine_used` per page and alarm when the fallback rate is non-trivial.
   *Do this first in Phase 2 — it is cheap and it makes 6 and 7 verifiable.*

## Phase 3 — Post-correction and validation (this is where 99% on fields comes from)

9. **Repair the mojibake in `ocr_domain_ur.py` and `ocr_text.py`** (F5) —
   `.encode('cp1252').decode('utf-8')` on every corrupted literal, strip the BOMs, and
   add a unit test asserting the constants contain real `؀-ۿ` characters so it cannot
   regress.
10. **Wire domain normalization into the pipeline** — it currently isn't called anywhere.
    Note this means deciding where it lives: the microservice returns raw text, so
    normalization belongs backend-side, post-response.
11. **Field-level validators:** CNIC check-format, date plausibility, khasra/khewat
    format, area-unit arithmetic consistency, amount-in-words vs amount-in-digits
    cross-check. Anything failing validation → NeedsReview, never auto-filled.
    Party-role names on Pakistani sale deeds use a recital clause parser
    (`sale_deed_clauses.py`, F10) so reviewable candidates are actual names, not
    boilerplate.
12. **Urdu wordlist for Tesseract** (`--user-words`) built from the repaired domain
    vocabulary. Depends on 9.

## Phase 4 — Honest quality gating

13. **Replace `quality.py`'s scoring** (F8): drop the word-count/length proxies; base the
    score on engine confidence distribution, script-consistency ratio,
    garbage/replacement-char ratio, and dictionary hit-rate. Fix the word-vs-line
    confusion. Remove the `0.5` default-confidence fudge.
14. **Recalibrate `autofill_eligible`** (`ocr_pipeline.py:142`) against the measured
    field-accuracy curve, so the auto-accept threshold is derived from data rather than
    the current guessed 0.45/0.7 split.

---

## Verification gate

No accuracy claim gets made until Phase 0 is done and a before/after run exists on the
same sample set. Every phase re-runs the eval and the numbers go in `04_worklog.md`.

Phases 1–4 are ordered by expected value, but that ordering rests on the **estimated**
causal weights at the bottom of `02_findings.md`. Once the Phase 0 baseline exists,
re-check the ordering against measured per-fix deltas and reorder if the data disagrees.
