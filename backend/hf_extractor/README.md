# HF Extractor Service

A Dockerized FastAPI service for document entity extraction using Hugging Face models (currently with mock CNIC extraction).

## Overview

This service exposes:
- `GET /health` - Health check endpoint
- `POST /v1/extract` - Entity extraction endpoint

## Running Locally

### Using Docker Compose

The service is integrated into the main `docker-compose.yml`. To start it:

```bash
docker compose up -d --build hf-extractor
```

### Standalone

```bash
cd backend/hf_extractor
docker build -t hf-extractor .
docker run -p 8090:8090 \
    -e MODEL_NAME=microsoft/layoutxlm-base \
    -e EXTRACTOR_VERSION=layoutxlm-v1 \
    -e DEVICE=cpu \
    hf-extractor
```

## API Usage

### Health Check

```bash
curl http://localhost:8090/health
```

Response:
```json
{"ok": true}
```

### Extract Entities

```bash
curl -X POST http://localhost:8090/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "550e8400-e29b-41d4-a716-446655440000",
    "page_no": 3,
    "image": {
      "content_type": "image/png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    },
    "ocr": {
      "engine": "paddleocr",
      "page_confidence": 0.85,
      "words": ["CNIC:", "12345-1234567-1", "Name:", "John", "Doe"],
      "boxes": [[10, 10, 50, 20], [60, 10, 180, 20], [190, 10, 230, 20], [240, 10, 270, 20], [280, 10, 310, 20]],
      "normalized": true
    },
    "options": {
      "extractor_version": "layoutxlm-v1",
      "return_token_spans": true,
      "language_hint": "en"
    }
  }'
```

Expected Response:
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "page_no": 3,
  "extractor": {
    "name": "layoutxlm",
    "model": "microsoft/layoutxlm-base",
    "fine_tuned": false,
    "version": "layoutxlm-v1"
  },
  "entities": [
    {
      "label": "CNIC",
      "value": "12345-1234567-1",
      "confidence": 0.95,
      "source": {
        "ocr_engine": "paddleocr",
        "token_indices": [1],
        "bbox": [60.0, 10.0, 180.0, 20.0],
        "bbox_norm_1000": [60, 10, 180, 20]
      },
      "evidence": {
        "snippet": "12345-1234567-1",
        "page_no": 3
      }
    }
  ],
  "quality": {
    "page_corrupted": false,
    "page_ocr_confidence": 0.85
  }
}
```

## Current Implementation

- **Mock CNIC Extractor**: Simple regex-based extractor that identifies Pakistani CNIC numbers
- **Pattern Matching**: Supports formats like `12345-1234567-1` or `1234512345671` (13 digits)
- **No Hallucination**: Entity values are only assembled from OCR tokens using `token_indices`
- **Confidence**: 0.95 for exact matches, 0.0 (filtered out) for non-matches

## Environment Variables

- `MODEL_NAME`: Model identifier (default: `microsoft/layoutxlm-base`)
- `EXTRACTOR_VERSION`: Extractor version (default: `layoutxlm-v1`)
- `DEVICE`: Device to use (default: `cpu`)

## Logging

The service logs structured information for each extraction request:
- `doc_id`, `page_no`, `ocr_engine`, `word_count`, `box_count`
- `extracted_entities_count`

### OCR Routing Options (Prompt 8)

Additional optional fields in `options`:
- `min_ocr_confidence`: Minimum OCR confidence threshold (0.0-1.0, default: `0.55`)
- `enable_ocr_fallback`: Enable automatic OCR fallback if primary OCR confidence is low (default: `true`)
- `force_ocr_fallback`: Force fallback OCR to run regardless of primary confidence (default: `false`, for testing)

### OCR Routing and Fallback

The hf-extractor service implements confidence-driven OCR routing:

1. **Primary OCR**: Runs Tesseract with PSM=6 (uniform block of text) and OEM=1 (LSTM)
2. **Fallback OCR**: If primary confidence < `min_ocr_confidence` OR word count < 10, runs Tesseract with PSM=11 (sparse text)
3. **Selection**: Chooses the best result by:
   - Higher page confidence (wins)
   - If tie, more words (wins)

The selected OCR result is used for entity extraction. OCR routing metadata is included in the response `quality` field and persisted in `evidence_json` when entities are saved.

#### Force Fallback for Testing

To force fallback OCR to run (useful for testing):

```bash
curl -X POST http://localhost:8090/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "123e4567-e89b-12d3-a456-426614174000",
    "page_no": 1,
    "image": {
      "content_type": "image/png",
      "base64": "..."
    },
    "ocr": null,
    "options": {
      "extractor_version": "layoutxlm-v1",
      "return_token_spans": true,
      "language_hint": "mixed",
      "force_ocr_fallback": true,
      "enable_ocr_fallback": true,
      "min_ocr_confidence": 0.55
    }
  }'
```

#### Logging

OCR routing decisions are logged with prefix `HF_EXTRACTOR_OCR`:

```
HF_EXTRACTOR_OCR: doc_id=... page=1 used_fallback=true selected_conf=0.72 selected_psm=11 attempts=2
```

Extraction results are logged with prefix `HF_EXTRACTOR_EXTRACT`:

```
HF_EXTRACTOR_EXTRACT: doc_id=... page=1 entities_by_label={'CNIC': 2, 'PLOT_NO': 1} total_entities_count=3
```

## Fine-tuning LayoutXLM (Offline)

The hf-extractor service supports fine-tuned LayoutXLM models for token-classification. This section documents the complete offline training and deployment workflow.

### Prerequisites

- Label Studio installed and running locally
- Python environment with training dependencies (see `scripts/training/requirements-train.txt`)
- Access to document images and OCR tokens

### Step 1: Label Data in Label Studio

1. Import your document images into Label Studio
2. Load the Label Studio configuration:
   ```bash
   # Import the config in Label Studio UI or via API
   # Config file: scripts/training/label_studio_config_layoutxlm.xml
   ```
3. Label entities by drawing rectangles around words and selecting the appropriate label:
   - **PERSON_NAME** (hotkey: `p`)
   - **CNIC** (hotkey: `c`)
   - **PLOT_NO** (hotkey: `l`)
   - **SCHEME_NAME** (hotkey: `s`)
   - **REGISTRY_NO** (hotkey: `r`)
   - **DATE** (hotkey: `d`)
   - **AMOUNT** (hotkey: `a`)

**Important**: Label only the exact words that belong to each entity. Avoid labeling full sentences. Prefer minimal spans.

### Step 2: Export JSON from Label Studio

1. Export your labeled tasks from Label Studio:
   - Via UI: Export → JSON (Min)
   - Via API: `GET /api/projects/{project_id}/export?exportType=JSON`

2. Save the export to a file (e.g., `labelstudio_export.json`)

### Step 3: Convert to Training Dataset

Run the converter script to create JSONL training datasets:

```bash
cd scripts/training
python export_labelstudio_to_layoutxlm.py \
    --input labelstudio_export.json \
    --out_train datasets/train.jsonl \
    --out_val datasets/val.jsonl \
    --tokens_dir data/ocr_tokens \
    --split_ratio 0.9
```

**Parameters**:
- `--input`: Label Studio JSON export file
- `--out_train`: Output path for training JSONL
- `--out_val`: Output path for validation JSONL
- `--tokens_dir`: (Optional) Directory containing OCR token JSON files (sidecar format)
- `--split_ratio`: Train/val split ratio (default: 0.9)

**Note**: If OCR tokens are not in the Label Studio export, provide them as sidecar JSON files:
- Format: `{task_id}_tokens.json` with structure:
  ```json
  {
    "words": ["word1", "word2", ...],
    "bboxes_norm_1000": [[x0, y0, x1, y1], ...]
  }
  ```

The converter will:
- Map Label Studio rectangle annotations to OCR word indices via IoU/center-point matching
- Assign BIO labels with priority resolution (CNIC > AMOUNT > DATE > ...)
- Validate alignment and label consistency
- Split into train/val sets

### Step 4: Train Model

Train a fine-tuned LayoutXLM model:

```bash
cd scripts/training
python train_layoutxlm_token_cls.py \
    --model microsoft/layoutxlm-base \
    --train_data datasets/train.jsonl \
    --val_data datasets/val.jsonl \
    --output_dir models/layoutxlm-tokencls-v1 \
    --epochs 5 \
    --lr 5e-5 \
    --batch_size 2 \
    --grad_accum 8
```

**CPU Training** (default):
- `--batch_size 2`: Small batch size for CPU
- `--grad_accum 8`: Gradient accumulation to simulate larger batch
- Remove `--fp16` flag (not supported on CPU)

**GPU Training** (if CUDA available):
```bash
python train_layoutxlm_token_cls.py \
    --model microsoft/layoutxlm-base \
    --train_data datasets/train.jsonl \
    --val_data datasets/val.jsonl \
    --output_dir models/layoutxlm-tokencls-v1 \
    --epochs 5 \
    --lr 5e-5 \
    --batch_size 8 \
    --grad_accum 4 \
    --fp16
```

The training script will:
- Load processor and model from HuggingFace
- Prepare datasets with proper tokenization
- Train using Transformers Trainer
- Compute precision/recall/F1 metrics per label and overall
- Save model and processor to `output_dir`

### Step 5: Evaluate Model (Optional)

Evaluate the trained model on a test set:

```bash
cd scripts/training
python eval_layoutxlm_token_cls.py \
    --model models/layoutxlm-tokencls-v1 \
    --eval_data datasets/test.jsonl \
    --output_metrics metrics.json
```

### Step 6: Deploy Fine-tuned Model

To use the fine-tuned model with hf-extractor:

1. **Build hf-extractor with ML dependencies**:
   ```bash
   INSTALL_ML_DEPS=1 docker compose build hf-extractor
   ```

2. **Mount model directory into container**:
   
   Option A: Volume mount in `docker-compose.yml`:
   ```yaml
   hf-extractor:
     volumes:
       - ./models/layoutxlm-tokencls-v1:/models/layoutxlm:ro
   ```
   
   Option B: Copy model into container during build (modify Dockerfile)

3. **Set environment variables**:
   
   In `docker-compose.yml` or `.env`:
   ```yaml
   hf-extractor:
     environment:
       HF_LAYOUTXLM_MODEL_PATH: /models/layoutxlm
       HF_DEVICE: cpu  # or "cuda" if GPU available
   ```
   
   For api/worker services:
   ```yaml
   api:
     environment:
       HF_EXTRACTOR_VERSION: layoutxlm-v1
       HF_EXTRACTOR_ENABLE_LAYOUTXLM: "true"
   ```

4. **Restart services**:
   ```bash
   docker compose up -d --build hf-extractor api worker
   ```

5. **Verify model loading**:
   Check hf-extractor logs for:
   ```
   Loading LayoutXLM model from: /models/layoutxlm
   LayoutXLM model loaded successfully
   ```

### Safety and Validation

**Important**: The fine-tuned model still enforces "copy-only" extraction:
- All entity values are assembled strictly from OCR tokens using `token_indices`
- No generative text - values come only from OCR words array
- Low-confidence predictions should still require user confirmation
- The model assists extraction but does not replace validation

### Troubleshooting

- **Model not loading**: Check `HF_LAYOUTXLM_MODEL_PATH` and ensure model directory contains `config.json`, `pytorch_model.bin` (or `.safetensors`), and processor files
- **CUDA out of memory**: Reduce `--batch_size` or increase `--grad_accum`
- **Training too slow**: Use GPU if available, or reduce `--max_length`
- **Low F1 scores**: Check label quality in Label Studio, ensure sufficient training data, consider adjusting learning rate or epochs

