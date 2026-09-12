# Urdu OCR Evaluation Dataset

This directory contains a "golden dataset" for evaluating Urdu OCR accuracy and preventing regressions.

## Structure

```
datasets/urdu_ocr/
├── README.md (this file)
├── manifests/
│   ├── manifest.json (repository-local template)
│   └── cds_gold_001_draft_pilot.json (external three-page pilot)
├── samples/ (gitignored - never commit PDFs)
│   ├── sample1.pdf
│   ├── sample1.page1.txt (ground truth for page 1)
│   └── sample1.page2.txt (ground truth for page 2)
└── reports/ (gitignored - generated reports)
    ├── 20240101_120000_report.json
    └── latest_report.md
```

## Adding Samples

1. **Place PDF files** in `samples/` directory (never commit to git)
2. **Create ground truth text files** (required for accuracy claims):
   - Name format: `{sample_id}.page{N}.txt` (1-based page numbers)
   - Can be partial (key lines only) - F1 score handles this well
   - Transcribe independently from the scan; do not copy OCR output
   - Have an Urdu-capable reviewer approve the transcription
3. **Update manifest.json**:
   ```json
   {
     "id": "sample1",
   "source_pdf": "02_ADDITIONAL_EVIDENCE/sample1.pdf",
   "document_class": "fard",
   "rulebook_targets": ["GOLD-EX-001"],
   "pages": [
       {
         "page": 1,
         "ground_truth_path": "transcriptions/sample1.page1.txt",
         "human_verified": true
       }
     ],
     "notes": "Description of sample"
   }
   ```

## Creating Ground Truth

Ground truth files must contain an independently reviewed transcription of the
expected text for each page. Until a reviewer approves the text, the page may
be used for a smoke test but not for an accuracy claim:

- **Full text**: Complete page text (best for CER/WER)
- **Partial text**: Key lines only (F1 score works well with this)
- **Format**: Plain text, UTF-8 encoding
- **Normalization**: Will be normalized during evaluation (digits, Unicode, whitespace)

Example ground truth (`sample1.page1.txt`):
```
فرد نمبر 12345
کھاتہ نمبر 450
خسرہ 27/2/27
```

## Running Evaluation

### Local engine comparison

Install the local OCR dependencies in a dedicated virtual environment, then
run the comparison:

```bash
python -m venv .venv-ocr
.venv-ocr\\Scripts\\python.exe -m pip install -r ocr_service/requirements.txt
```

```bash
python scripts/dev/eval_local_ocr.py --engine both
```

This renders benchmark PDFs and runs Tesseract and PaddleOCR locally on the
same pages. It fails when a referenced scan or reviewed transcription is
missing, and records CER, WER, F1, confidence, CDS quality, elapsed time, and
memory delta. It also saves raw OCR text under `reports/raw/` and reports
weighted corpus CER/WER totals rather than only averaging page percentages.

For the external CDS-GOLD-001 pilot, keep the PDFs and drafts outside Git and
run:

```powershell
.venv-ocr\Scripts\python.exe scripts/dev/eval_local_ocr.py `
  --manifest datasets/urdu_ocr/manifests/cds_gold_001_draft_pilot.json `
  --data-root C:\path\to\CDS_GOLD_001_URDU_PDF_CORPUS `
  --engine paddleocr --dpi 150 --allow-unverified
```

`--allow-unverified` is required for draft comparisons and marks the report
`DRAFT_REFERENCE_ONLY` / `NOT_RELEASE_ACCURACY`. Omit it for a release
candidate run; unverified pages are then rejected.

### Quick Mode (Quality Metrics Only)

```bash
python scripts/dev/eval_urdu_ocr.py --mode quick
```

This mode:
- Runs OCR on all samples
- Computes quality metrics (Urdu ratio, garbage ratio, confidence)
- Shows routing decisions (PDF text layer, ensemble, layout)
- Does NOT require ground truth files

### Full Mode (With Accuracy Metrics)

```bash
python scripts/dev/eval_urdu_ocr.py --mode full
```

This mode:
- Does everything in quick mode
- Additionally computes CER/WER/F1 if ground truth files exist
- Requires ground truth files for accuracy metrics

### With Failure Threshold

```bash
python scripts/dev/eval_urdu_ocr.py --mode full --fail-cer 0.25
```

Exits with code 1 if average CER exceeds 0.25 (useful for CI gating).

## Interpreting Metrics

### Quality Metrics

- **Urdu ratio**: Proportion of Urdu/Arabic characters (0.0-1.0)
  - Higher is better for Urdu documents
- **Garbage ratio**: Proportion of replacement characters (0.0-1.0)
  - Lower is better (should be < 0.02)
- **Confidence**: OCR confidence score (0.0-1.0)
  - Higher is better

### Accuracy Metrics (requires GT)

- **CER (Character Error Rate)**: Edit distance / GT length (0.0 = perfect)
  - Lower is better
  - Baseline: ≤ 0.28 for scanned Urdu, ≤ 0.10 for native text PDFs
- **WER (Word Error Rate)**: Word-level edit distance (0.0 = perfect)
  - Lower is better
- **F1**: Token overlap score (0.0-1.0, 1.0 = perfect)
  - Higher is better
  - Works well with partial ground truth

### Routing Decisions

- **PDF text layer used**: Percentage of pages using native PDF text extraction
  - Higher is better (faster, more accurate)
- **Ensemble PaddleOCR winner**: Percentage where PaddleOCR won ensemble comparison
- **Layout OCR used**: Percentage where layout segmentation improved results

## Suggested Baseline Thresholds

For regression testing, consider these thresholds:

- **Scanned Urdu PDFs**:
  - Average CER ≤ 0.28
  - Average garbage ratio ≤ 0.02
  - Average Urdu ratio ≥ 0.15 (if Urdu content expected)

- **Native Text PDFs**:
  - Average CER ≤ 0.10
  - PDF text layer usage ≥ 80% (should prefer native extraction)

- **Mixed Documents**:
  - Average confidence ≥ 0.60
  - Garbage ratio ≤ 0.02

## CI Integration

The evaluation can be integrated into CI pipelines:

```bash
# Non-blocking (always passes)
scripts/ci/urdu_ocr_eval.sh

# Blocking (fails if threshold exceeded)
URDU_OCR_GATE=true scripts/ci/urdu_ocr_eval.sh
```

Set `URDU_OCR_GATE=true` environment variable to enable failure on threshold violations.

## Notes

- **Never commit PDFs**: Samples directory is gitignored
- **Ground truth is optional**: Quality metrics work without GT
- **Partial GT is fine**: F1 score handles key lines only
- **Per-page evaluation**: Each page evaluated independently
- **Routing visibility**: Shows which OCR features were used per page
