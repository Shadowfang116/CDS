# Worklog

## Current state — OVERWRITE THIS BLOCK, don't append to it

| | |
|---|---|
| **Last updated** | 2026-08-25 |
| **Phase** | Matter Workbench product phase — Phase 1 shell |
| **Branch** | `refactor/cds-backend-core` |
| **Live case** | RUN 3 flagship `38e6069e-4c3d-4a41-94c8-8b9ecc92e069`. Visual corpus RUN 2 `5bcdb8eb-…`. Do not use RUN 1 `4673c7f2-…`. |
| **Findings** | F10 🟢, F11 🟢, F12 🟢. Open: F7, F8. In progress: F3, F6. |
| **Baseline CER/WER/F1** | ❌ pending sample PDFs (Q1) |
| **Next action** | Backend gold gaps re-verified by focused pytest. No backend patch needed from current evidence; next backend proof should be a fresh live RUN 3 only if new end-to-end evidence is required. |

---

## Log — append new entries at the top

### 2026-08-25 — Backend gold verification only (no backend code changes)

Scope was limited to backend files, backend tests, and AI context evidence for the
remaining CDS original master plan gold gaps named after RUN 2.

- Reviewed `AI_context/02_findings.md` and `AI_context/execution_reports/CDS_GOLD_001_RUN2_EXPLANATION_AND_NEXT_STEPS.md` against the current backend tests.
- Re-ran focused backend proof only:
  `python -m pytest backend/tests/test_cds_gold_001_semantics.py backend/tests/test_contextual_autofill.py backend/tests/test_exception_waivable.py backend/tests/test_next_action.py -q`
- Result: `32 passed, 1 warning in 2.63s`. The warning is the existing default `APP_SECRET_KEY` config warning from `backend/app/core/config.py`.
- Verified current tests still cover the named gold gaps:
  sale deed area extraction/comparison, explicit Fard issue date parsing, historical-tax evidence detection, and waiver preservation / next-action behavior.
- Because the focused proof is already green, no backend code change was justified in this pass.

Evidence record: `AI_context/execution_reports/05_cds_gold_backend_verification_2026-08-25.md`.

### 2026-08-19 — Matter Workbench Phase 1 shell

Frontend-only. No backend semantic change. No Inbox.

- Audit vs Figma 01 + RUN 3 spec: Decision Strip was missing borrower, blocker, readiness, hard-stop; File/Work were not collapsible.
- Header now derives borrower/regime/facility from existing workbench `fields[]`. Decision is never inferred from High count.
- File and Work panes are collapsible; Evidence stays primary.
- Tests: `npm run test:workbench` + typecheck after this pass.

No CER claimed.

### 2026-08-18 — Backend freeze-and-delete cleanup

Notes: `AI_context/backend_simplification/`. Branch `refactor/cds-backend-core`.

- S0/S1 inventory. No Exception+CP merge. No Finding table.
- S2 `GET /cases/{id}/workbench` + façades. Matter `load()` uses the read model.
- S3 deleted two `.bak` files. Left phase10 and frozen analytics registered.
- S4 deprecated direct waive; ExceptionsPanel still calls it.
- S5 active `docs/rulepacks/punjab_mortgage_v1.yaml`; archived KYC-02/05/07/10; tests keep `05_rulepack_v1.yaml`.
- S6 documented Celery → ocr_pipeline → ocr_service; Stack B not deleted.

No CER claimed.

### 2026-08-18 — Matter workbench against gold legal findings

File | Evidence | Work can now replay RUN 2/RUN 3 without leaving Matter.

- Findings show `GOLD-*-01`, description, required evidence, and jump to source page.
- File pane lists canonical types + OCR status; missing instruments for the selected finding; Extract (`autofill overwrite=false`) and Evaluate on the matter.
- Waive proposes `exception_waive` (reason dialog). Decide splits waiver vs case decision. Checker ≠ maker. Re-eval after waiver approve.
- Draft/issue pack lists exports and download when `succeeded`.
- Tests: `npm run test:workbench` passed. Live RUN 2/RUN 3 walk not run — API/frontend were down.

No CER claimed.

### 2026-08-17 — CDS-GOLD-001 RUN 3 complete

Matter `38e6069e-4c3d-4a41-94c8-8b9ecc92e069`. Report: `execution_reports/04_cds_gold_001_run3.md`.

Initial FAIL with 7 gold findings including area mismatch, stale Fard from `15 جنوری 2026`, and historic tax. Additional batch cleared area/plan/dues/encumbrance/Fard/name. GOLD-TAX stayed open, reviewer proposed waiver, admin approved, re-eval kept it Waived, decision PASS, bank pack queued.

### 2026-08-17 — F12 gold fact extraction (area / Fard date / historic tax)

RUN 2 proved pipeline + classification + arbitration + remediation. It did not
fire area mismatch or historic tax, and it treated Fard upload time as issue date.

- Prefer `کل رقبہ` totals; `کنال` / OCR `JUS` = kanal; skip 1-kanal khasra pieces.
- `گست` → August only when it is not already `اگست`. Locale-independent month parse.
- Newest Fard without a parseable issue date → `Fard date unconfirmed`, not current.
- GOLD-TAX keywords include `تاریخی`, `paper receipt`, `waiver scenario`, `20-2019`.
- `run_rules` does not reopen Waived/Resolved rule ids. Decision uses live exception rows.
- E2E title is RUN 3; reviewer proposes GOLD-TAX waiver, admin approves, then bank pack.

Tests: 175 targeted passed (`test_cds_gold_001_semantics` + rulepack + mvp + autofill).

### 2026-08-17 — CDS-GOLD-001 RUN 2 live comparison

Matter `5bcdb8eb-75bc-440b-9bcb-3a963b574360`. Full report: `execution_reports/03_cds_gold_001_semantics.md`.

- Seller `محمد اکرم` and buyer `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ` survived the additional-batch autofill (`clause_urdu`, sale deed). Plot `82` / block `B` kept.
- All 16 files classified to the canonical vocabulary (Sale Deed, Possession Letter, Fard, NOC, Search Report, …).
- Initial evaluate: 5 gold findings (PLAN, DUES, ENCUMB, NAME, FARD). No salary-slip / photograph / false missing title / false missing possession.
- Additional batch resolved PLAN, DUES, ENCUMB, NAME. After rebuilding evaluators, re-eval is PASS (stale Fard uses newer Fard upload time; area no longer compares unrelated docs).
- GOLD-AREA did not fire on the initial batch (no sale-deed kanal fact). GOLD-TAX never opened (no historic-tax keyword captured).

### 2026-08-17 — F11 CDS-GOLD-001 semantics (arbitration, classification, gold rules)

Branch `fix/cds-gold-001-semantics`. No Surya/Paddle/frontend work.

- Candidate arbitration is source-aware: `(case_id, field_key, document_id)`. Later mutation cannot replace sale-deed `clause_urdu`. Conflicts are preserved and marked for review.
- Mutation form labels rejected. Sale-deed detection requires strong markers; mutation is penalized. Party roles only on `sale_deed`.
- Canonical `doc_type` vocabulary persisted after OCR, before `run_rules`. Filename is a hint; content classifies when OCR exists.
- Document facts: area, issue date, owner name, dues language, charge ref, tax history.
- Gold rules GOLD-AREA-01, GOLD-PLAN-01, GOLD-DUES-01, GOLD-ENCUMB-01, GOLD-FARD-01, GOLD-NAME-01, GOLD-TAX-01. Existing KYC photo/salary/utility/co-applicant rules apply to `borrower_type: individual` only.
- Worker default rulepack path walks parents to `docs/05_rulepack_v1.yaml` (Docker `/app/docs/...`). Compose still sets `RULEPACK_PATH`. `pilot_real_case.ps1` uses `/auth/login`.

Tests: 165 targeted passed; 188 backend tests passed (host `jwt` missing for `test_exception_waivable.py` only).

### 2026-08-17 — CDS-GOLD-001 live E2E

Full report: `execution_reports/02_cds_gold_001_e2e.md`.

- Uploaded 11 initial + 5 additional Urdu PDFs. OCR Done on all 16 (Tesseract fallback).
- Initial autofill: plot `82`, block `B`, seller `محمد اکرم`, buyer `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ` via `clause_urdu`.
- Second autofill overwrite from mutation replaced party names with `رجسٹریشن حوالہ` / `/ منتقل الیہ`.
- Rulepack decision FAIL (24→25 missing-doc exceptions). Gold content defects (area mismatch, stale fard, name variant) were not raised. Building-plan missing dropped after additional evidence.

### 2026-08-17 — F10 contextual autofill (WS4.2 party names)

Test case 1 (`01697780-20a0-4544-92e5-d74639a6d893`) before this pass:

- `property.plot_number` = `82` (correct)
- `property.block` = `B` (correct)
- `party.seller.names` = clause leftover including buyer company (wrong)
- `party.buyer.names` = `درج ذیل شرائط پر متفق ہوئے۔` (wrong)
- `party.witness.names` = `CDS-GOLD-001 | فرضی تربیتی` (wrong)

After (pytest on the same OCR strings, 8 passed):

- seller → `محمد اکرم` via `clause_urdu`, offsets not page 0
- buyer → `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ`
- witness omitted
- plot `82` / block `B` still extract from sale deed and PT-10
- PT-10 does not emit party roles
- No CER claimed (D4). Autofill still writes candidates only (D7).

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

### 2026-08-26 — Runtime OCR/workbench verification

- Docker OCR health endpoint returned 200 and identified `ocr_service` as healthy.
- Startup logs show `requested_backend=surya` and `effective_backend=tesseract`; Surya is unavailable in the image and the service falls back to Tesseract.
- On seeded `PILOT DEMO CASE`, authenticated workbench extraction returned 200 and evaluation returned 200 with findings and a blocked `FAIL` decision.
- The workbench then reported one source document, findings, and `readiness=False`.
- No OCR accuracy percentage is claimed: representative ground-truth samples remain unavailable, and the Surya fallback is an explicit release limitation.
