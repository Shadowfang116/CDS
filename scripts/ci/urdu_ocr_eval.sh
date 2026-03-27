#!/bin/bash
# Phase 9: Urdu OCR evaluation CI hook (non-blocking by default)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST_PATH="$PROJECT_ROOT/datasets/urdu_ocr/manifests/manifest.json"
SAMPLES_DIR="$PROJECT_ROOT/datasets/urdu_ocr/samples"

# Check if manifest exists
if [ ! -f "$MANIFEST_PATH" ]; then
    echo "Manifest not found: $MANIFEST_PATH"
    echo "Skipping Urdu OCR evaluation"
    exit 0
fi

# Check if any sample PDFs exist
if [ ! -d "$SAMPLES_DIR" ] || [ -z "$(find "$SAMPLES_DIR" -name "*.pdf" -type f 2>/dev/null)" ]; then
    echo "No sample PDFs found in $SAMPLES_DIR"
    echo "Skipping Urdu OCR evaluation"
    exit 0
fi

# Determine mode based on URDU_OCR_GATE environment variable
if [ "$URDU_OCR_GATE" = "true" ]; then
    echo "Running Urdu OCR evaluation with gate (will fail on threshold violation)"
    MODE="full"
    FAIL_CER="--fail-cer 0.30"
else
    echo "Running Urdu OCR evaluation (quick mode, non-blocking)"
    MODE="quick"
    FAIL_CER=""
fi

# Run evaluation
cd "$PROJECT_ROOT"
python scripts/dev/eval_urdu_ocr.py \
    --manifest "$MANIFEST_PATH" \
    --out "$PROJECT_ROOT/datasets/urdu_ocr/reports" \
    --mode "$MODE" \
    $FAIL_CER

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Urdu OCR evaluation completed successfully"
else
    echo "Urdu OCR evaluation failed (threshold exceeded)"
fi

exit $EXIT_CODE
