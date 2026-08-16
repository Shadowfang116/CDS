# Runbook — getting to a measurable environment

All paths relative to `/Users/itsmibrahim/Documents/Fahad Proj/CDS` unless stated.

> ⚠️ **Verification status:** the commands below were derived by reading
> `docker-compose.yml`, `ocr_service/main.py`, `ocr_service/schemas.py` and
> `scripts/dev/eval_urdu_ocr.py` at `b94bb10`. **They have not been executed** —
> Docker is installed (29.2.1) but was not running when this was written, and the host
> has no OCR toolchain. Expect to correct them on first real use, and update this file
> when you do.

---

## 0. Why you can't just run it locally

The host has **no** `tesseract` binary and **none** of `cv2`, `numpy`, `PIL`,
`pytesseract`, `surya`, `paddleocr`, `pdf2image`. Installing them natively on macOS
(especially `surya-ocr` + torch) is slow and will not match the container the service
actually runs in.

**Use Docker.** `ocr_service/` has its own image and its own `requirements.txt`.

Quick confirmation of the local state:

```bash
which tesseract || echo "no tesseract"
python3 -c "import cv2, numpy, PIL, pytesseract" 2>&1 | tail -1
docker info >/dev/null 2>&1 && echo "docker running" || echo "docker NOT running"
```

## 1. Start Docker, then the OCR service alone

You do **not** need the full stack (db, redis, minio, api, worker, frontend) to measure
OCR. The microservice is standalone on port 8001.

```bash
open -a Docker            # then wait for the daemon
docker compose up -d --build ocr_service
docker compose logs -f ocr_service
```

Watch the startup log. `main.py:86-88` logs a warning if Surya was requested but
resolved to Tesseract — **that warning firing is F3 reproducing itself.** Capture it;
it is the cheapest confirmation of the single largest finding.

Health check:

```bash
curl -s localhost:8001/health
```

## 2. Call `/ocr` directly

This is the endpoint production uses. Request shape from `ocr_service/schemas.py`:

```jsonc
{
  "document_id": "smoke-test",
  "pages": ["<base64 PNG>", "..."],   // base64-encoded PNG bytes, no data: prefix
  "engine": "surya"                    // or "tesseract"
}
```

```bash
B64=$(base64 -i /path/to/page.png | tr -d '\n')
curl -s localhost:8001/ocr \
  -H 'Content-Type: application/json' \
  -d "{\"document_id\":\"smoke\",\"pages\":[\"$B64\"],\"engine\":\"surya\"}" \
  | python3 -m json.tool
```

**Check `engine_used` in the response.** If you asked for `surya` and got
`"engine_used": "tesseract"`, F3 is confirmed live, not just by code reading.

## 3. Ground truth

Drop samples into `datasets/urdu_ocr/samples/` following
`datasets/urdu_ocr/README.md`. The existing manifest
(`datasets/urdu_ocr/manifests/manifest.json`) expects:

```
datasets/urdu_ocr/samples/sample1.pdf
datasets/urdu_ocr/samples/sample1.page1.txt     # ground truth, page 0
datasets/urdu_ocr/samples/sample1.page2.txt     # ground truth, page 1
```

Add manifest entries for each new document. The directory is **gitignored** — samples
live on disk only, never in the repo.

## 4. Run the eval

⚠️ **This does not work yet — F7.** `scripts/dev/eval_urdu_ocr.py:16` imports
`ocr_page_pdf` from `app.services.ocr_engine`, but it is defined in `app.services.ocr`.
Fix that import first (Phase 0.1).

Once fixed, the CLI is:

```bash
python scripts/dev/eval_urdu_ocr.py \
  --manifest datasets/urdu_ocr/manifests/manifest.json \
  --out datasets/urdu_ocr/reports \
  --mode full \
  --fail-cer 0.28
```

- `--mode quick` = quality signals only; `--mode full` = adds CER/WER/F1.
- `--fail-cer` exits 1 above the threshold. `0.28` is the repo's own scanned-Urdu bar
  (`datasets/urdu_ocr/README.md`).

**Caveat that matters:** this harness calls `ocr_page_pdf` → **Stack B**, which is not
what production runs. Repairing the import makes it execute, not makes it relevant.
Phase 0.3 adds a `POST /ocr` eval so the measured thing is the served thing.

## 5. The CI wrapper

```bash
URDU_OCR_GATE=true bash scripts/ci/urdu_ocr_eval.sh
```

⚠️ Without `URDU_OCR_GATE=true` it runs quick mode and never fails. **And with no
samples present it prints "Skipping" and `exit 0` regardless** (`:20-24`) — so a green
CI run currently means nothing. Phase 0.4 makes missing samples a hard failure.

---

## Useful one-liners

```bash
# Re-verify every finding at once (from repo root)
grep -n "adaptiveThreshold\|fastNlMeansDenoising\|NORM_MINMAX" ocr_service/preprocessing.py   # F1
grep -n "mu11\|mu20" ocr_service/preprocessing.py                                             # F2
grep -n "import surya.ocr" ocr_service/engines/surya_engine.py                                # F3
grep -n "psm 6" ocr_service/engines/tesseract_engine.py                                       # F4
grep -n "from app.services.ocr_engine import ocr_page_pdf" scripts/dev/eval_urdu_ocr.py       # F7
grep -n "OCR_IMAGE_MAX_SIDE" backend/app/core/config.py                                       # F9

# Which engine is configured vs which actually runs
grep -n "OCR_ENGINE" docker-compose.yml
docker compose logs ocr_service | grep -i "falling back\|unavailable"

# Rebuild just the OCR service after editing it
docker compose up -d --build ocr_service

# Regenerate the line counts in 01_repo_map.md
find ocr_service -name '*.py' | xargs wc -l | sort -n
ls backend/app/services/ocr*.py | xargs wc -l | sort -n
```
