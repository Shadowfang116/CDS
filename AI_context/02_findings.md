# Findings — why OCR accuracy is ~65%

All findings verified against `CDS` @ **`b94bb10`** (branch `feat/ocr-accuracy-improvements`).
Re-verified 2026-08-15.

Every finding carries a **re-verify command**. Run it from the repo root
(`/Users/itsmibrahim/Documents/Fahad Proj/CDS`) before trusting the `file:line`
references below — they drift as soon as anyone edits these files.

---

## Status

| ID | Status | Est. impact | Primary location |
|---|---|---|---|
| F1 | 🟢 fixed (2026-08-16) | large | `ocr_service/preprocessing.py` |
| F2 | 🟢 fixed (2026-08-16) | large | `ocr_service/preprocessing.py` |
| F3 | 🟡 in progress (observability added 2026-08-16) | large | `ocr_service/engines/surya_engine.py` |
| F4 | 🟢 fixed (2026-08-16) | medium-large | `ocr_service/engines/tesseract_engine.py` |
| F5 | 🟢 fixed (2026-08-16) | small-medium | `backend/app/services/ocr_domain_ur.py` |
| F6 | 🟡 in progress | medium | `backend/app/core/config.py` |
| F7 | 🔴 open | blocks all verification | `scripts/dev/eval_urdu_ocr.py:16` |
| F8 | 🔴 open | affects trust, not raw CER | `ocr_service/quality.py:38-43` |
| F9 | 🟢 fixed (2026-08-16) | medium | `backend/app/core/config.py`, `ocr_service/preprocessing.py` |
| F10 | 🟢 fixed (2026-08-17) | field accuracy (names) | `backend/app/services/extractors/party_roles.py`, `sale_deed_clauses.py` |
| F11 | 🟢 fixed (2026-08-17) | candidate overwrite + noisy rules | `dossier_autofill.py`, `canonical_docs.py`, `docs/05_rulepack_v1.yaml` |
| F12 | 🟢 fixed (2026-08-17) | gold area / fard date / historic tax | `document_facts.py`, `rule_engine.py`, `docs/05_rulepack_v1.yaml` |

Status values: 🔴 open · 🟡 in progress · 🟢 fixed (date + commit) · ⚪ won't fix (reason).
**Update this table in the same session you change the code.**

Impact column is an *estimate*, not a measurement. Nothing here has been measured —
see F7. Confirm or discard these weights once a baseline exists.

---

## F1. The preprocessor destroys the page before OCR sees it

`ocr_service/preprocessing.py:51-60`

```python
def preprocess_page(image: np.ndarray) -> np.ndarray:
    gray = _to_grayscale(image)
    thresholded = _adaptive_threshold(gray)          # 1-bit, blockSize=31, C=11
    deskewed = _deskew(thresholded)                  # rotates the BINARY image
    if _should_denoise(deskewed):                    # true when <= 4 MP
        processed = cv2.fastNlMeansDenoising(deskewed, None, 18, 7, 21)
    else:
        processed = deskewed
    normalized = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX)
    return normalized
```

Four separate problems:

1. **Hard adaptive-threshold before a neural engine.** Surya (and PaddleOCR) are
   trained on natural grayscale/RGB document images. A 1-bit image is far outside
   their training distribution. Binarization is a Tesseract-era trick; it should
   never be applied ahead of a DL recognizer, and even Tesseract 4/5 LSTM prefers
   a clean grayscale image over a hand-binarized one.
2. **`fastNlMeansDenoising` on an already-binary image** with `h=18`. Non-local-means
   on a two-valued image smears glyph edges and eats the thin connecting strokes
   that Nastaliq Urdu depends on. This is actively destructive.
   Note it is *conditional* on `_should_denoise` (≤ 4 MP) — but with
   `OCR_IMAGE_MAX_SIDE = 2200` (F9) a page is at most ~3.7 MP, so **it fires on
   essentially every real page.**
3. **`cv2.normalize(..., NORM_MINMAX, 0, 255)` on a 0/255 image is a no-op.** Dead line.
4. **Fixed `blockSize=31`** regardless of image resolution. At 300 DPI that block is
   ~2.6 mm; at a low-res scan it spans several glyphs. Should scale with text height.

**Re-verify:**
```bash
grep -n "adaptiveThreshold\|fastNlMeansDenoising\|NORM_MINMAX" ocr_service/preprocessing.py
```
**Still broken if:** all three appear, in that order, inside `preprocess_page`.

## F2. The deskew estimator is mathematically wrong for pages of text

`ocr_service/preprocessing.py:24-43`

```python
moments = cv2.moments(255 - binary)
angle = 0.5 * np.arctan2(2.0 * moments["mu11"], moments["mu20"] - moments["mu02"])
angle_degrees = float(np.degrees(angle))
if abs(angle_degrees) < 0.1 or abs(angle_degrees) > 15:
    return binary
```

This is the **second-order-moment principal-axis** formula. It estimates the
orientation of a *single blob* (it is the classic MNIST digit-deskew trick). Applied
to a whole page of text, the second moments are dominated by the overall rectangular
ink distribution, not by the baselines. On a multi-column or stamped page it returns
an essentially arbitrary angle, and the code then rotates by up to 15°.

A wrong 5–15° rotation on a text page is catastrophic for line segmentation, and
`INTER_CUBIC` on a binary image re-introduces grey halos that F1's denoise then
smears into mush.

**A correct `minAreaRect`-based deskew capped at 5° already exists** at
`backend/app/services/ocr_preprocess.py:146`. The microservice just doesn't use it.

**Re-verify:**
```bash
grep -n 'mu11\|mu20\|mu02' ocr_service/preprocessing.py
```
**Still broken if:** the moment-ratio formula is still what `_deskew` uses.

## F3. Surya almost certainly never runs — everything silently falls back to Tesseract

`ocr_service/engines/surya_engine.py:28-30`, `139-142`

```python
import surya.ocr as surya_ocr
runner = getattr(surya_ocr, "run_ocr", None) or getattr(surya_ocr, "ocr", None)
...
try:
    raw_result = runner(pil_image)
except TypeError:
    raw_result = runner([pil_image])
```

Two failure modes, both ending in Tesseract:

- **Modern surya-ocr (v0.6+)** removed the `surya.ocr` module entirely; recognition is
  now `surya.recognition.RecognitionPredictor` + `surya.detection.DetectionPredictor`
  (and a `FoundationPredictor` in recent versions). The `import surya.ocr` raises,
  the `except Exception` at line 38 sets `_SURYA_AVAILABLE = False`, and
  `_resolve_engine_name` (`main.py:48-51`) rewrites every request to `"tesseract"`.
- **Legacy surya-ocr** where `surya.ocr.run_ocr` did exist took six required args
  (`images, langs, det_model, det_processor, rec_model, rec_processor`).
  `runner(pil_image)` → `TypeError`; the retry `runner([pil_image])` raises
  `TypeError` again, which is **not** covered by the inner `except TypeError` (that
  only wraps the first call). It propagates to the outer `except Exception` at
  line 143 → `quality_level="unavailable"` → `main.py:140-143` falls back to Tesseract.

`ocr_service/requirements.txt` pins nothing (`surya-ocr` is unversioned), so which
failure mode you get depends on install date.

Compounding it: `docker-compose.yml:76` sets `OCR_ENGINE: ${OCR_ENGINE:-surya}` — so
the *configured* default is Surya, and operators have every reason to believe it is
running.

**Net effect: the "surya" default engine is decorative. 100% of pages are OCR'd by
Tesseract, on a binarized+denoised image.** That combination alone plausibly explains
most of the 35-point gap.

Also: no model warm-up. Even once fixed, the first request pays full model-load
latency inside the request.

**Re-verify:**
```bash
grep -n "import surya.ocr\|run_ocr" ocr_service/engines/surya_engine.py
grep -n "surya" ocr_service/requirements.txt          # unpinned == still fragile
```
**Still broken if:** the import targets `surya.ocr`, or the requirement has no `==`.

## F4. Tesseract is invoked with the wrong settings

`ocr_service/engines/tesseract_engine.py:43-51`

```python
config = "--oem 1 --psm 6 -l urd+eng"
text = pytesseract.image_to_string(pil_image, config=config).strip()
data = pytesseract.image_to_data(pil_image, config=config, output_type=...DICT)
```

- **`--psm 6` = "assume a single uniform block of text."** Real land-record / court
  documents have headers, stamps, tables and multiple columns. PSM 6 forces them into
  one block and scrambles reading order. PSM 3 (auto) or PSM 4 (single column,
  variable size) is the right default, ideally chosen per page.
- **`-l urd+eng` in one pass.** Urdu is RTL Nastaliq, English is LTR Latin. Tesseract
  runs a single LSTM over the combined charset; the mixed-direction hypothesis space
  measurably degrades both. Better: detect dominant script per region, run separate
  passes, merge by bbox.
- **No DPI hint.** Without `--dpi`, Tesseract guesses from the image, and guesses badly
  on rescaled input. It wants ~300 DPI and ~30-33 px cap height.
- **OCR runs twice per page** — `image_to_string` then `image_to_data` — doubling cost,
  and the two calls can disagree. Note the returned `text` comes from the *first* call
  while `word_boxes` come from the second, so text and boxes are not guaranteed
  consistent. Text should be reconstructed from the `image_to_data` dict (respecting
  `block_num`/`par_num`/`line_num`) in a single pass.
- **No `--user-words` / no domain wordlist**, despite the repo carrying an extensive
  Urdu legal/property vocabulary in `ocr_domain_ur.py`.
- **No confidence-based filtering** — `_normalize_confidence` drops only negative
  values, so words at conf 0-20 (pure noise) are kept and averaged into the score.

**Re-verify:**
```bash
grep -n "psm 6\|image_to_string\|image_to_data\|--dpi" ocr_service/engines/tesseract_engine.py
```
**Still broken if:** `psm 6` is present, `--dpi` is absent, and both `image_to_*`
calls remain.

## F5. `ocr_domain_ur.py` is 931 lines of dead code — every Urdu literal is mojibake

`backend/app/services/ocr_domain_ur.py`

The Urdu constants were saved through a UTF-8 → cp1252 round-trip. Measured with the
re-verify command below:

| File | Mojibake tokens | Real Urdu chars | BOM |
|---|---|---|---|
| `ocr_domain_ur.py` | 42 | **0** | yes |
| `ocr_text.py` | 2 | **0** | yes |

⚠️ **The token count is regex-dependent — do not treat it as canonical.** A stricter
character class gives 21 for `ocr_domain_ur.py`; the command below gives 42. The number
that matters and does not move is the third column: **`real_urdu_chars = 0`.** If you
change the detection regex, change this table to match, or the two will drift apart.

```python
URDU_MONTHS = {
    "Ø¬Ù†ÙˆØ±ÛŒ": 1, "ÙØ±ÙˆØ±ÛŒ": 2, ...   # should be جنوری, فروری, ...
}
text = text.replace('Û”', '.').replace('ØŒ', ',')   # should be ۔ and ،
```

Confirmed reversible: `'Û”'.encode('cp1252').decode('utf-8')` → `'۔'` (U+06D4, Urdu
full stop); `'ØŒ'` → `'،'` (U+060C, Arabic comma); `'Ù…Ø±Ø¨Ø¹'` → `'مربع'`.

The load-bearing fact is the last column: **zero real Urdu characters in a module
whose entire purpose is matching Urdu.** No Urdu month, punctuation rule, keyword or
property-reference pattern in it can ever match real OCR output. Date normalization,
CNIC extraction, khasra/khewat parsing and area-unit conversion are all silently
no-ops on Urdu input.

> **Correction (2026-08-15):** an earlier draft of this file claimed "235 mojibake
> sequences". That number was not reproducible by any detection regex tried here.
> The conclusion is unchanged and, if anything, starker: **0 real Urdu chars.**

**Re-verify:**
```bash
python3 -c "
import re
for p in ['backend/app/services/ocr_domain_ur.py','backend/app/services/ocr_text.py']:
    s=open(p,encoding='utf-8-sig').read()
    cands=set(re.findall(r'[ -ÿŒœŠšŽžƒ–-⁄€™]{2,}', s))
    ok=[c for c in cands if re.search(r'[؀-ۿ]', c.encode('cp1252','ignore').decode('utf-8','ignore'))]
    print(p, 'mojibake_tokens=', len(ok), 'real_urdu_chars=', len(re.findall(r'[؀-ۿ]', s)))
"
```
**Still broken if:** `real_urdu_chars=0` while `mojibake_tokens>0`.

## F6. The whole "Phase 4 / 7 / 9" OCR upgrade was never wired to config

These settings are referenced in code but **do not exist in
`backend/app/core/config.py`** (verified: 0 occurrences each):

| Setting | Referenced by | Effect of absence |
|---|---|---|
| `OCR_PADDLE_LANG` | `ocr_paddle.py:38,76` | `AttributeError` the moment PaddleOCR is called |
| `OCR_PADDLE_USE_ANGLE_CLS` | `ocr_paddle.py:38,96` | same |
| `OCR_PADDLE_USE_GPU` | `ocr_paddle.py:40` | same |
| `OCR_ENABLE_ENSEMBLE` | ensemble gate | ensemble unreachable |
| `OCR_ENABLE_LAYOUT` | `ocr_layout.py` gate | layout OCR unreachable |
| `OCR_ENABLE_PDF_TEXT_LAYER` | `eval_urdu_ocr.py:82` | native-text shortcut unreachable |
| `OCR_PDF_TEXT_LAYER_ENGINE` | `eval_urdu_ocr.py:90` | same |

So PaddleOCR ensemble, layout segmentation, and the PDF-text-layer fast path — the
three features the dataset README advertises as routing decisions — are all
non-functional. `ocr_service/requirements.txt` doesn't list `paddleocr` either.

**Biggest single miss in that list: the PDF text-layer path.** Any PDF that already
carries an embedded text layer should be read directly (≈100% accurate, ~0 ms) instead
of being rasterized and re-OCR'd at 65%. `backend/app/services/pdf_text_layer.py`
(217 lines) exists and is gated behind a setting that was never added.

**Re-verify:**
```bash
for s in OCR_PADDLE_LANG OCR_PADDLE_USE_ANGLE_CLS OCR_PADDLE_USE_GPU \
         OCR_ENABLE_ENSEMBLE OCR_ENABLE_LAYOUT OCR_ENABLE_PDF_TEXT_LAYER \
         OCR_PDF_TEXT_LAYER_ENGINE; do
  printf '%-30s %s\n' "$s" "$(grep -c "$s" backend/app/core/config.py)"
done
```
**Still broken if:** any count is `0`.

## F7. The evaluation harness does not import — and CI hides it

`scripts/dev/eval_urdu_ocr.py:16`

```python
from app.services.ocr_engine import ocr_page_pdf
```

`ocr_page_pdf` is defined in `app/services/ocr.py:203`, **not** in `ocr_engine.py`.
The script raises `ImportError` before doing anything.

**Worse: there is no CI gate at all.** Two layers of nothing:

1. `scripts/ci/urdu_ocr_eval.sh` **is not referenced anywhere in
   `.github/workflows/ci.yml`.** It has never run in CI.
2. Even run manually, it checks for sample PDFs and, finding none, prints "Skipping"
   and **exits 0** (`:20-24`) — so it cannot fail, and never reaches the ImportError.

And the surrounding CI is just as empty of coverage: **no Python test job exists**
(`pytest` isn't even a declared dependency), the `docker-build` job builds only the
**api** and **frontend** images — never `ocr_service` — and the `smoke` job starts
`api db redis minio`, never `ocr_service`. See `08_master_plan.md` §1.

**Net: nothing in CI touches the OCR system. A contributor can break OCR completely and
CI stays green.**

`datasets/urdu_ocr/samples/` does not exist; the manifest's single entry (`sample1`)
points at `sample1.pdf` / `sample1.page1.txt` / `sample1.page2.txt`, none of which are
in the repo. There is no ground truth anywhere.

**Implication: there is currently no way to reproduce or verify the 65% figure, and no
way to prove any improvement.** Fixing this is prerequisite to everything else.

Second-order problem: even once the import is fixed, this harness exercises
`ocr_page_pdf` → **Stack B**, which is not what production runs (see `01_repo_map.md`).
It would measure dead code. Phase 0 must add a microservice-level eval that hits
`POST /ocr` directly.

**Re-verify:**
```bash
grep -n "from app.services.ocr_engine import ocr_page_pdf" scripts/dev/eval_urdu_ocr.py
grep -n "def ocr_page_pdf" backend/app/services/ocr.py backend/app/services/ocr_engine.py
ls datasets/urdu_ocr/samples/ 2>&1
grep -n "urdu_ocr_eval\|pytest\|ocr_service" .github/workflows/ci.yml || echo "OCR ABSENT FROM CI"
```
**Still broken if:** the import line matches, `def ocr_page_pdf` appears only in
`ocr.py`, the samples dir is missing, and the CI grep finds nothing.

## F8. Quality scoring measures verbosity, not accuracy

`ocr_service/quality.py:38-43`

```python
word_count_score = min(word_count / 40.0, 1.0)
avg_chars_score  = min(avg_chars_per_word / 5.0, 1.0)
quality_score = (word_count_score * 0.45) + (avg_chars_score * 0.35) + (mean_box_confidence * 0.20)
```

80% of the score is "did we emit a lot of longish tokens" — which garbage OCR does very
well. Only 20% comes from engine confidence. **A page of hallucinated noise scores
*higher* than a correctly-read sparse page.**

This matters because the score drives whether a page is marked `autofill_eligible`
(`ocr_pipeline.py:142`: `quality_level in {"good", "fair"}`). Thresholds are guesses.

> **Correction (2026-08-17):** autofill does **not** write `case_dossier_fields`.
> It writes `ocr_extraction_candidates` (Pending). Dossier upsert happens on
> **confirm**. Bad OCR can still produce garbage *candidates*; it does not silently
> fill the customer dossier. See D7.

Two more bugs in the same area:
- `mean_box_confidence` **defaults to `0.5`** when no confidences exist
  (`quality.py:34-36`), quietly inflating scores for engines that report nothing.
- The `avg_chars_per_word < 2.5` cutoff (`quality.py:45`) is applied to whatever
  nodes the engine returned. For Surya, `_extract_nodes` (`surya_engine.py:70`)
  walks `("words", "lines", "text_lines", "tokens", "pages")` in order — modern Surya
  results expose `text_lines`, not `words`, so **line-level nodes get treated as
  "words"** and the threshold means something completely different per engine.

> **Correction (2026-08-15):** an earlier draft cited `surya_engine.py:156-170` for the
> line-vs-word confusion. The traversal order that causes it is defined at line 70;
> 156-170 is only where the nodes are consumed.

**Re-verify:**
```bash
sed -n '34,45p' ocr_service/quality.py
grep -n "autofill_eligible" backend/app/services/ocr_pipeline.py
```
**Still broken if:** the 0.45/0.35/0.20 weighting and the `else 0.5` default remain.

## F9. Rendering / resolution issues upstream of the service

- **Pages are downscaled ~37% before OCR.** `backend/app/core/config.py:137` sets
  `OCR_IMAGE_MAX_SIDE = 2200`; A4 at 300 DPI is ~3508 px on the long side. The cap is
  applied on the production render path — `tasks_ocr.py::_render_page_pdf_to_base64_png`
  → `ocr.pdf_to_image` → `ocr_engine.pdf_to_image_dynamic(max_side=...)`
  (`ocr.py:67`). For Nastaliq, where diacritics and dot-groups are a few pixels wide,
  that is a direct accuracy loss.
- **Page images are shipped as base64 PNG inside a JSON body** (`tasks_ocr.py:27-32`).
  Large pages become multi-MB JSON strings. This is also *why* the resolution cap
  feels necessary — the transport is the constraint, not the OCR.
- **No upscaling for low-DPI source scans.** A 150 DPI fax-quality scan is fed to
  Tesseract as-is, where 2× upscaling is known to help substantially.
- **No orientation (OSD) check in the microservice at all.** A 90°/180° rotated scan
  returns near-total garbage. `ocr_engine.py:187-201` implements this correctly — but
  it is on the unused Stack B.

**Re-verify:**
```bash
grep -n "OCR_IMAGE_MAX_SIDE" backend/app/core/config.py
grep -rn "osd\|OSD\|image_to_osd" ocr_service/ | head
```
**Still broken if:** the cap is `2200` and the OSD grep returns nothing.

---

## F10. Party-role extractors assume labelled forms; sale deeds are running clauses

`backend/app/services/extractors/party_roles.py`, `sale_deed_clauses.py`

Test case 1 (`01_Registered_Sale_Deed_URDU.pdf`) OCR already contained the real names:

- seller `محمد اکرم ولد محمد یوسف`
- buyer `اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ`

Autofill instead wrote:

- seller = clause leftover starting `ایک جانب, اور خریدار کمپنی…`
- buyer = `درج ذیل شرائط پر متفق ہوئے۔`
- witness = watermark `CDS-GOLD-001 | فرضی تربیتی` at confidence 0.85

Cause: labelled-form extractors (`فروخت کنندہ` + colon + next line). Pakistani recitals
have no colon. Evidence `find(snippet)` missed and fell back to **page start**.
`مالک` was treated as a seller marker. Plot `82` / block `B` were already correct.

**Fix (2026-08-17):** clause parser first (`clause_urdu`); doc-class routing; garbage
blocklist; real char offsets (no page-0 fallback); method confidence; labelled paths
must not overwrite a clause hit. Pytest: `backend/tests/test_contextual_autofill.py`.

**Re-verify:**
```bash
cd backend
python -m pytest tests/test_contextual_autofill.py -q
```
**Still broken if:** seller is not `محمد اکرم`, buyer is not the textile company,
witness is non-empty on the recital fixture, or plot/block are not `82` / `B`.

---

## F11. RUN 1 persistence destroyed better party candidates; rules were the wrong 28

CDS-GOLD-001 RUN 1 (`4673c7f2-5f39-4ebb-8f4a-4406fab0decc`) proved the remaining
defects were product semantics, not OCR:

1. Autofill looked up the first Pending row by `field_key` and overwrote it, including
   `document_id`. Sale-deed `clause_urdu` names became mutation labels
   (`رجسٹریشن حوالہ`, `/ منتقل الیہ`).
2. `detect_sale_deed` treated a single `خریدار` / `فروخت` as enough; mutation entered
   the party-role path.
3. `doc_type` was not a stable canonical vocabulary, so REG_001 / POS-01 fired while
   the sale deed and possession letter were on the matter.
4. The MVP 28-rule pack has no applicability. A company mortgage was hit with
   photograph / salary-slip / utility-bill / co-applicant rules. Gold legal facts
   (area, stale fard, name variant) were not extracted or evaluated.

**Fix (2026-08-17, branch `fix/cds-gold-001-semantics`):** source-aware arbitration;
mutation-label refusal; canonical `doc_type` persisted before `run_rules`; document
facts (area/date/owner/dues/charge); gold rules GOLD-AREA-01 … GOLD-TAX-01;
`applies_when` on retail KYC/SOC/LDA/society-transfer rules; inferred
`case.borrower_type` written like regime (D9); worker rulepack path
`/app/docs/05_rulepack_v1.yaml`.

**RUN 2** `5bcdb8eb-75bc-440b-9bcb-3a963b574360`: 5 gold findings on the initial
batch (not 24–25 generic cards); seller/buyer not overwritten; additional evidence
cleared plan/dues/encumbrance/name. Remaining gaps moved to F12.

**Re-verify:**
```bash
cd backend
python -m pytest tests/test_contextual_autofill.py tests/test_cds_gold_001_semantics.py tests/test_rule_engine_mvp.py -q
```

Keep RUN 1 as contaminated evidence. Do not design Findings UX against it.

---

## F12. RUN 2 did not extract the remaining gold legal facts

Tesseract already had the gold strings. Extractors missed the real spellings:

1. Area unit is `کنال` (noon). OCR often reads it as Latin `JUS`. Totals are on
   `کل رقبہ` lines. Khasra fragments (`1 کنال 10 مرلہ`) were stored instead of
   4 Kanal / 3 Kanal 18 Marla, so GOLD-AREA-01 never had two comparable facts.
2. Corrected Fard `تاریخ اجرا 8 گست 2026` (`گست` = OCR of `اگست`) was not parsed.
   Stale-document then treated `created_at` as the issue date, so a Fard uploaded
   today looked current.
3. PT-10 historic-tax wording is `تاریخی paper receipt` / `20-2019` / `Waiver scenario`,
   not `previous year`. GOLD-TAX-01 never opened, so the waiver path was untested.
4. Re-running rules after a waiver recreated an Open GOLD-TAX row because Waived
   exceptions were not preserved.

**Fix (2026-08-17):** prefer `کل رقبہ` totals; treat `کنال|کانال|kanal|jus` as kanal;
parse `گست` without rewriting `اگست`; do not use upload time as issue date
(missing date → unconfirmed); expand GOLD-TAX keywords; skip recreating Waived
rules. E2E script is RUN 3 (waiver + bank pack).

**Re-verify:**
```bash
cd backend
python -m pytest tests/test_cds_gold_001_semantics.py -q
```

---

## Estimated causal weight

**These are estimates from code reading, not measurements.** Nothing in this table has
been confirmed against ground truth — that is exactly what F7 blocks. Treat the
ordering as a hypothesis to test in Phase 0, not as a result.

| # | Cause | Est. contribution |
|---|---|---|
| F3 | Surya never runs → Tesseract-only | large |
| F1/F2 | Destructive binarize + denoise + bad deskew | large |
| F4 | psm 6, mixed urd+eng, no DPI hint | medium-large |
| F9 | Downscaling to 2200 px, no OSD, no upscaling | medium |
| F6 | PDF text-layer path dead (native-text PDFs re-OCR'd) | medium, document-mix dependent |
| F5 | Urdu post-correction dead | small-medium (post-processing) |
| F8 | Quality gate lets bad pages through | affects trust, not raw accuracy |
| F10 | Party extractors grab boilerplate on Urdu recitals | field accuracy (names) — fixed 2026-08-17 |
| F7 | No measurement | blocks all verification |
