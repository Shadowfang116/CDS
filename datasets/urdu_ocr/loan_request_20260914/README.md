# Urdu OCR review corpus — loan request case

Status: `DRAFT_UNVERIFIED`. Text has not been checked by an Urdu reader. Where line counts aligned, the label keeps the existing CDS transcription; otherwise it uses the Tesseract control candidate and preserves the comparison fields in JSON. Do not use these labels as ground truth yet.

This package follows PaddleOCR dataset conventions: recognition labels are one UTF-8 line per image with `image<TAB>text`; detection labels are `page_image<TAB>JSON`, where each JSON item has `transcription` and four-point `points`. The source page images are preserved in `images/`; line crops are in `line_crops/`; per-page traceable labels are in `labels/*.json`.

Because the OCR response saved for this case did not include reusable word boxes, the current line boxes come from a Tesseract control pass and are grouped word boxes. They are tighter than the first scaffold, but still require visual verification for Urdu. During verification, replace each line text with the exact visible text and tighten or correct each polygon to the visible line. The JSON also keeps a `candidate_text_tesseract` field for comparison. Set `human_verified: true`, add reviewer/date, and change the status to `VERIFIED`.

The corpus has 18 pages from 11 source PDFs and 575 automatically grouped line crops. It is kept as a single review split to avoid pretending this small case is a train/validation benchmark. After verification, create document-level train/validation/test splits so pages from one document never leak across splits.

Files:
- `labels/rec_gt_unverified.txt`: recognition training format.
- `labels/det_gt_unverified.txt`: detection training format.
- `labels/*.json`: page/line traceability.
- `manifests/review_status.csv`: reviewer checklist.
- `manifests/pages.jsonl`: page manifest.
