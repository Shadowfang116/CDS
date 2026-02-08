# LayoutXLM Token-Classification Dataset Format

This directory contains the training datasets in JSONL format (one JSON object per line).

## Dataset Format

Each line is a JSON object with the following structure:

```json
{
  "id": "<doc_id>_<page_no>",
  "image_path": "data/images/<id>.png",
  "words": ["word1", "word2", "word3", ...],
  "bboxes_norm_1000": [[x0, y0, x1, y1], [x0, y0, x1, y1], ...],
  "labels": ["O", "B-CNIC", "I-CNIC", "O", ...]
}
```

### Fields

- **id**: Unique identifier for the page (format: `<doc_id>_<page_no>`)
- **image_path**: Relative path to the image file (PNG format)
- **words**: List of OCR-detected words (strings)
- **bboxes_norm_1000**: List of bounding boxes, one per word, in normalized 0-1000 coordinates
  - Format: `[x0, y0, x1, y1]` where (x0, y0) is top-left and (x1, y1) is bottom-right
  - Coordinates are normalized to a 0-1000 scale regardless of original image size
- **labels**: List of BIO tags, one per word
  - **O**: Outside any entity
  - **B-<LABEL>**: Beginning of an entity (e.g., `B-CNIC`, `B-PERSON_NAME`)
  - **I-<LABEL>**: Inside an entity (e.g., `I-CNIC`, `I-PERSON_NAME`)

### Constraints

- **Length alignment**: `len(words) == len(bboxes_norm_1000) == len(labels)`
- **Valid labels**: All labels must be one of:
  - `O` (outside)
  - `B-PERSON_NAME`, `I-PERSON_NAME`
  - `B-CNIC`, `I-CNIC`
  - `B-PLOT_NO`, `I-PLOT_NO`
  - `B-SCHEME_NAME`, `I-SCHEME_NAME`
  - `B-REGISTRY_NO`, `I-REGISTRY_NO`
  - `B-DATE`, `I-DATE`
  - `B-AMOUNT`, `I-AMOUNT`
- **BIO consistency**: `I-<LABEL>` must follow `B-<LABEL>` or `I-<LABEL>` of the same label type

### Example

```json
{
  "id": "doc_001_1",
  "image_path": "data/images/doc_001_1.png",
  "words": ["Name", ":", "John", "Doe", "CNIC", "12345-1234567-1"],
  "bboxes_norm_1000": [[100, 50, 150, 70], [155, 50, 165, 70], [170, 50, 210, 70], [215, 50, 245, 70], [300, 50, 340, 70], [345, 50, 480, 70]],
  "labels": ["O", "O", "B-PERSON_NAME", "I-PERSON_NAME", "O", "B-CNIC"]
}
```

## File Organization

- `train.jsonl`: Training dataset (typically 90% of data)
- `val.jsonl`: Validation dataset (typically 10% of data)

## Generation

These files are generated from Label Studio exports using the `export_labelstudio_to_layoutxlm.py` converter script.

