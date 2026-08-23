# Master plan — contributing to the OCR system

**What this is:** the execution plan. How work on the OCR system gets broken into
shippable units, verified, and landed.

**What this is not:** the technical roadmap. *What* to fix and *why* lives in
`03_plan.md`; the evidence lives in `02_findings.md`. This document is *how it lands*.

Read `01_repo_map.md` before touching anything, or you will improve code that does not
run.

---

## 1. Ground truth: how this repo currently accepts changes

Verified against `b94bb10`. **This section is the reason the plan is shaped the way it
is.** Every assumption a contributor would normally make about this repo is wrong.

| Assumption | Reality |
|---|---|
| "CI runs the tests" | ❌ **`.github/workflows/ci.yml` has no Python test job at all.** Frontend lint/typecheck/build, Docker build, API smoke. That's it. |
| "pytest is set up" | ❌ **`pytest` is not a declared dependency.** `backend/tests/run_mvp_tests.py` is a hand-rolled importlib loop that only ever loads `test_rule_engine_mvp.py`. |
| "CI builds the OCR service" | ❌ The `docker-build` job builds **api** and **frontend** images only. `ocr_service/Dockerfile` is never built in CI. |
| "CI exercises OCR" | ❌ The smoke job starts `api db redis minio`. **`ocr_service` is never started.** |
| "There's an OCR accuracy gate" | ❌ `scripts/ci/urdu_ocr_eval.sh` **is not referenced anywhere in `ci.yml`.** It is dead. And if run manually with no samples it `exit 0`s (F7). |
| "There are OCR tests" | ❌ **Zero.** No `test_*ocr*` anywhere in the repo. |
| "CI will run on my branch" | ❌ Triggers are `push`/`pull_request` to `main`/`master` only. Nothing runs on `feat/*` until a PR is opened. |

Two more that shape the work:

- **Verification here is PowerShell + manual.** `scripts/dev/` holds ~15 `verify_*.ps1`
  scripts, including `verify_urdu_ocr.ps1` and `verify_ocr_review_flow.ps1`. That is the
  team's actual QA mechanism. Respect it — ship a verification path, not just a diff.
- **Python version skew.** `ocr_service/Dockerfile` is `python:3.11-slim`;
  `backend/pyproject.toml` requires `>=3.12`. Don't assume one environment.

**Consequence: nothing you change to the OCR system is currently caught by any automated
check.** A contributor can break OCR completely and CI stays green. This is why WS0 below
is not optional and not deferrable — it is the entire foundation.

## 2. Principles

1. **Fix what runs.** All changes land in `ocr_service/`. Where Stack B has a correct
   implementation, port it across (see D3 in `05_decisions.md`).
2. **Measurement precedes claims.** No accuracy number without a recorded run (D4).
3. **One concern per PR.** Every unit below is independently reviewable and
   independently revertable. Do not bundle a preprocessing rewrite with a transport
   change because both touch the OCR path.
4. **Every change ships its own verification.** A diff without a way to confirm it is
   not a contribution. In this repo that means: a test, a `verify_*` script, or a
   recorded eval delta — ideally the first.
5. **Fail loudly.** This codebase's defining pathology is silent degradation — a dead
   engine that looks alive (F3), a gate that passes because it skipped (F7), a config
   setting that silently doesn't exist (F6). Never add another. Prefer a crash to a
   fallback that hides itself.
6. **Leave the encoding better than you found it.** UTF-8, no BOM. Several files carry
   BOMs (`ocr_domain_ur.py`, `ocr_text.py`, `run_mvp_tests.py`, `run_unit_tests.ps1`) and
   one is fully mojibake'd (F5). Add BOMs to nothing.

## 3. Dependency graph

```
WS0  Make it verifiable  ──┬──> WS1  Correctness fixes (no engine change)
   (blocking, no user input) │
                            ├──> WS2  Engine replacement  ──> WS3  Ensemble
                            │
                            └──> WS4  Post-correction & validation
                                          │
WS5  Quality gating  <────────────────────┘  (needs WS4's field validators
                                              to calibrate against)
```

- **WS0 blocks everything.** Without it no change can be shown to help or hurt.
- **WS1 does not need samples** — these are unambiguous defects. It can proceed in
  parallel with gathering ground truth (Q1).
- **WS2 needs WS0's baseline** to be worth doing; a new engine with no measurement is a
  coin flip.
- **WS5 is last** because auto-accept thresholds must be calibrated against measured
  field accuracy, not guessed — guessing is the current bug.

---

## 4. Workstreams

Each unit is one PR. `DoD` = definition of done. Effort is rough: S = <½ day,
M = 1–2 days, L = 3+ days.

### WS0 — Make it verifiable (blocking prerequisite)

Nothing else counts until this exists. Covers `03_plan.md` Phase 0.

| # | Unit | Files | Effort | Depends on |
|---|---|---|---|---|
| 0.1 | Fix eval harness import | `scripts/dev/eval_urdu_ocr.py:16` | S | — |
| 0.2 | Add the 7 missing `OCR_*` settings | `backend/app/core/config.py` | S | — |
| 0.3 | Add pytest + a real test job to CI | `backend/pyproject.toml`, `.github/workflows/ci.yml` | M | — |
| 0.4 | Build + smoke `ocr_service` in CI | `.github/workflows/ci.yml` | M | — |
| 0.5 | Microservice-level eval hitting `POST /ocr` | new `scripts/dev/eval_ocr_service.py` | M | 0.4 |
| 0.6 | Make the accuracy gate fail loudly, and wire it into CI | `scripts/ci/urdu_ocr_eval.sh`, `ci.yml` | S | 0.5 |
| 0.7 | Populate ground truth | `datasets/urdu_ocr/samples/` | M | ⛔ Q1 (user) |
| 0.8 | Record the baseline | `04_worklog.md` | S | 0.5, 0.7 |

**0.1** — `ocr_page_pdf` is in `app.services.ocr`, not `app.services.ocr_engine`.
*DoD:* the script runs to completion against a manifest. *Verify:* `python
scripts/dev/eval_urdu_ocr.py --mode quick` exits 0 with no ImportError.

**0.2** — Add `OCR_PADDLE_LANG`, `OCR_PADDLE_USE_ANGLE_CLS`, `OCR_PADDLE_USE_GPU`,
`OCR_ENABLE_ENSEMBLE`, `OCR_ENABLE_LAYOUT`, `OCR_ENABLE_PDF_TEXT_LAYER`,
`OCR_PDF_TEXT_LAYER_ENGINE`. All default **off** — this unit makes gated code
*reachable*, it does not turn it on. Turning things on is WS2/WS3, separately measured.
*DoD:* the F6 re-verify command reports non-zero for all seven.

**0.3** — Declare `pytest` in `backend/pyproject.toml` (`[project.optional-dependencies]
dev`), add a `backend-tests` job to `ci.yml`. Keep `run_mvp_tests.py` working so nothing
regresses for whoever uses it. *DoD:* CI has a job that runs pytest and fails on a
deliberately broken test. **Prove it fails before you trust it green.**

**0.4** — Add `ocr_service` to the `docker-build` job; add it to the services started in
`smoke`; assert `GET /health` responds. *DoD:* a deliberate syntax error in
`ocr_service/main.py` turns CI red.

**0.5** — The existing harness calls `ocr_page_pdf` → Stack B, which does not serve
traffic. This unit adds an eval that POSTs base64 pages to `/ocr` and scores the
response, so **the measured thing is the served thing**. Reuse `ocr_eval.py`'s CER/WER/F1
— that code is fine. *DoD:* produces per-page and aggregate CER/WER/F1 against the
running container.

**0.6** — Missing samples must be a **hard failure**, not `exit 0`. Then reference the
script from `ci.yml`. *DoD:* deleting the samples dir turns CI red.

**0.7** — ⛔ Blocked on Q1. See `06_open_questions.md`.

**0.8** — Two consecutive identical runs, numbers into the worklog table.
*DoD:* a baseline CER/WER/F1 exists and is reproducible. **This is the gate for WS2+.**

### WS1 — Correctness fixes (no engine change, no samples needed)

Unambiguous defects. Each is independently valuable and independently revertable.

| # | Unit | Finding | Effort | Depends on |
|---|---|---|---|---|
| 1.1 | Repair mojibake + strip BOMs, with a regression test | F5 | M | 0.3 |
| 1.2 | Native-text PDF fast path | F6 | M | 0.2, 0.8 |
| 1.3 | Rewrite `preprocessing.py` | F1, F2 | M | 0.8 |
| 1.4 | Fix the Tesseract invocation | F4 | M | 0.8 |
| 1.5 | Raise `OCR_IMAGE_MAX_SIDE`, add upscaling + OSD | F9 | M | 0.8, H1 |
| 1.6 | Surface `engine_used`; alarm on fallback rate | F3 | S | 0.4 |

**1.1** — `.encode('cp1252').decode('utf-8')` on every corrupted literal in
`ocr_domain_ur.py` and `ocr_text.py`; strip BOMs. **Ship the regression test in the same
PR** — assert the constants contain characters in `؀-ۿ` and that no
`real_urdu_chars == 0` module survives. Without the test this silently regresses on the
next careless save, which is exactly how it got here.
*DoD:* F5's re-verify command reports `real_urdu_chars > 0` and `mojibake_tokens = 0`.

**1.2** — Wire `pdf_text_layer.py` in, gated on extracted-char-count + garbage ratio,
falling back to OCR when the layer is empty or garbage. Highest value-per-line in the
whole plan if the document mix has native-text PDFs (Q2).
*DoD:* a native-text PDF returns its embedded text without rasterizing; a scanned PDF
still routes to OCR. Both asserted by test.

**1.3** — Grayscale as the default engine input; binarized variant only for Tesseract;
port the `minAreaRect` deskew from `backend/app/services/ocr_preprocess.py:146`; drop
NLM-on-binary; scale `blockSize` with text height; delete the no-op `cv2.normalize`.
*Risk: medium — every page passes through this function.* Do it after 0.8, never before.
*DoD:* measured CER delta recorded; unit tests on `_deskew` with synthetic rotated pages.

**1.4** — Single `image_to_data` pass with reading-order reconstruction, `--psm` chosen
per page, explicit `--dpi`, confidence floor. *DoD:* one OCR call per page (assert it),
measured CER delta recorded.

**1.5** — `OCR_IMAGE_MAX_SIDE` 2200 → ≥3500; upscale low-DPI input; add OSD.
**Check H1 first** — OSD needs `osd.traineddata`, which may not be in the image.
*DoD:* a 180°-rotated test page comes back readable.

**1.6** — Cheap, and it makes WS2 verifiable. Right now `OCR_ENGINE=surya` and Tesseract
does the work with nothing reporting it. *DoD:* `engine_used` is visible per page and a
fallback-rate metric exists.

### WS2 — Engine replacement

| # | Unit | Finding | Effort | Depends on |
|---|---|---|---|---|
| 2.1 | Rewrite `surya_engine.py` against the current API | F3 | L | 0.8, 1.6 |
| 2.2 | Pin `surya-ocr` exactly; pre-download models in the image | F3 | S | 2.1 |
| 2.3 | Warm-load models at FastAPI startup | F3 | M | 2.1 |

**2.1** — `DetectionPredictor` + `RecognitionPredictor` (+ `FoundationPredictor` on
recent versions). *DoD:* `/ocr` with `engine=surya` returns `engine_used: "surya"` —
which 1.6 makes observable. Measured CER delta vs the Tesseract baseline.

**2.2** — `surya-ocr` is currently unversioned, so behaviour depends on install date.
Pin it, and **pre-download weights into the Docker image** — otherwise the first
production request pays a model download, inside the request, possibly with no network.

**2.3** — Load once at startup, batch across pages. *DoD:* second request is
substantially faster than first; cold-start cost is paid at boot, not by a user.

### WS3 — Ensemble (only if WS2's numbers justify it)

| # | Unit | Finding | Effort | Depends on |
|---|---|---|---|---|
| 3.1 | Add PaddleOCR to the service | F6 | M | 2.1 |
| 3.2 | Per-page/line winner selection | F6 | L | 3.1 |

**Explicit go/no-go:** only start WS3 if WS2 lands and measured CER is still above the
`datasets/urdu_ocr/README.md` bar (0.28 scanned / 0.10 native). An ensemble roughly
doubles inference cost and complexity; do not build it because it was previously
designed, build it because the numbers demand it. Note `paddleocr` is in neither
`ocr_service/requirements.txt` nor `backend/pyproject.toml`.

### WS4 — Post-correction & field validation

This is where "99% on the fields that matter" actually comes from.

| # | Unit | Effort | Depends on |
|---|---|---|---|
| 4.1 | Wire domain normalization into the pipeline | M | 1.1 |
| 4.2 | Field validators (CNIC, khasra/khewat, dates, areas, amounts) | L | 4.1 |
| 4.3 | Field-level accuracy metric + auto-accept rate in the eval | M | 0.5, 4.2 |
| 4.4 | Urdu `--user-words` wordlist for Tesseract | S | 1.1 |

**4.1** — Note the architectural decision this forces: the microservice returns raw
text, so normalization belongs backend-side, post-response. Decide and record it in
`05_decisions.md` before writing code.

**4.2** — Anything failing validation → NeedsReview, **never auto-filled**.
Party names (2026-08-17, F10): `sale_deed_clauses.py` parses Urdu recitals first;
`validators.is_extraction_garbage` refuses watermarks and clause leftovers;
`dossier_autofill` will not persist a party candidate without char offsets.
Pytest: `backend/tests/test_contextual_autofill.py`. CNIC/khasra/date/amount
validators in this unit remain as originally scoped.

**4.3** — Without this, Q3's "validated field accuracy" framing is unmeasurable and
therefore unclaimable.

### WS5 — Honest quality gating

| # | Unit | Finding | Effort | Depends on |
|---|---|---|---|---|
| 5.1 | Replace `quality.py` scoring | F8 | M | 0.8 |
| 5.2 | Recalibrate `autofill_eligible` against measured accuracy | F8 | M | 4.3, 5.1 |

**5.1** — Drop the word-count/length proxies; score on confidence distribution,
script-consistency, garbage ratio, dictionary hit-rate. Fix the word-vs-line confusion
(`surya_engine.py:70`). Remove the `0.5` default-confidence fudge.

**5.2** — Derive the threshold from the measured field-accuracy curve. The current
0.45/0.7 split is a guess, and it currently decides what gets auto-filled into a
customer dossier.

---

## 5. Open hypothesis to test first

### H1 — Tesseract may be missing `eng` and `osd` traineddata ⚠️ unverified

`ocr_service/Dockerfile:9-14` installs with `--no-install-recommends`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-urd
```

On Debian, `tesseract-ocr` *Recommends* (does not Depend on) `tesseract-ocr-eng` and
`tesseract-ocr-osd`. With `--no-install-recommends`, recommends are skipped. So the
image may contain **`urd` only**.

If so:
- `-l urd+eng` (F4) may be erroring or silently degrading — and every OCR result in the
  system is affected;
- **the OSD orientation fix in 1.5 cannot work at all**, because `image_to_osd` requires
  `osd.traineddata`.

**This is a 30-second check and it gates 1.4 and 1.5. Do it before either.**

```bash
docker compose build ocr_service
docker compose run --rm --entrypoint tesseract ocr_service --list-langs
```

Expected if the hypothesis holds: `urd` present, `eng` and `osd` absent.
**Fix if confirmed:** add `tesseract-ocr-eng tesseract-ocr-osd` to the Dockerfile — a
one-line change that may be one of the highest-value fixes in this entire plan.
Record the result in `04_worklog.md` either way, and promote it to F10 in
`02_findings.md` if confirmed.

---

## 6. Definition of Done

A unit is done when **all** of these hold. No exceptions for "obvious" changes — the
current state of this repo is what "obvious" changes with no verification produce.

- [ ] Lands in `ocr_service/` (or is explicitly justified as backend-side)
- [ ] One concern; independently revertable
- [ ] Automated verification exists: a test, or a `verify_*` script, or a recorded eval
      delta. **A test is preferred and required where one is possible.**
- [ ] The test was proven to fail before the fix, not just pass after
- [ ] If it touches OCR output: before/after CER/WER/F1 recorded in `04_worklog.md`
- [ ] Finding status updated in `02_findings.md` (🔴 → 🟢 + date)
- [ ] No new silent fallback; failures are visible
- [ ] Files written UTF-8 without BOM
- [ ] Any decision taken along the way recorded in `05_decisions.md`

## 7. Testing strategy

There are **zero** OCR tests today. Build up in this order:

1. **Pure-function unit tests first** (no OCR engine needed, run anywhere):
   `preprocessing._deskew` on synthetic rotated pages · `quality.score_page` on crafted
   inputs · the F5 mojibake regression · `pdf_text_layer` gating logic. These are cheap,
   fast, and cover a surprising share of the findings.
2. **Container integration tests** (need the image, not ground truth):
   `/health`; `/ocr` returns the engine it was asked for; a rotated page comes back
   readable; one OCR call per page.
3. **Accuracy regression** (needs ground truth): the eval from 0.5, gated at the repo's
   own bar — CER ≤ 0.28 scanned, ≤ 0.10 native.

Tier 1 and 2 need no user input and no samples. **Start there.**

## 8. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| A change silently degrades accuracy with nothing to catch it | high | WS0 first. This is the whole reason WS0 is blocking. |
| Preprocessing rewrite (1.3) regresses some document classes while improving others | high | Report per-class CER, not just the aggregate. Keep the old path behind a setting for one release. |
| Surya rewrite (2.1) balloons — new API, model loading, batching | medium | Timebox. 1.6 makes the fallback observable, so a partial Surya is safe to ship: it degrades visibly, not silently. |
| Model download at runtime in production | medium | 2.2 bakes weights into the image. |
| Transport change (base64→multipart) breaks the worker↔service contract | high | Separate PR, after 1.5 is measured. Never bundled. |
| Ground truth never arrives (Q1) | high | WS0.1–0.6 and all of WS1 proceed without it. Only 0.7/0.8 and the measured deltas stall. |
| No CI on `feat/*` branches | medium | Open a draft PR early so CI actually runs. |

## 9. Conventions

- **Branch:** work continues on `feat/ocr-accuracy-improvements`. For units large enough
  to review separately, cut `feat/ocr-<unit>` off it (e.g. `feat/ocr-preprocessing`).
- **Commits:** repo style is mixed — recent commits are plain imperative sentence case
  ("Remove prompt planning residue from repo"), older ones use conventional prefixes
  ("feat:", "chore:"). **Match the recent style.** Reference the finding: `Fix moment-based
  deskew in OCR preprocessing (F2)`.
- **PRs:** open as draft early so CI runs (it doesn't run on `feat/*` pushes). Body
  should state: which finding, how it was verified, the measured delta if any, and what
  was deliberately left out.
- **Push access is untested** (D1). Test it before the first PR is due, not when it is.

## 10. Picking up work in a fresh session

1. Read `README.md` → current state; `04_worklog.md` → what happened last.
2. Check `06_open_questions.md` — most questions have a documented default. Only Q1 is
   genuinely blocking, and only for measurement.
3. Re-verify the finding you're about to fix (`02_findings.md` has a command for each).
   Do not trust `file:line` without running it.
4. Pick the lowest-numbered unit whose dependencies are met.
5. Work it to the Definition of Done in §6 — including the status update and worklog
   entry. Those are part of the unit, not cleanup for later.

**If you're starting right now, in order:** H1 (30 seconds, may be the highest-value
fix here) → 0.1 → 0.2 → 0.3 → 0.4. None need user input.
