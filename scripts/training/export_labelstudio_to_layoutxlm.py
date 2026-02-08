#!/usr/bin/env python3
"""
Convert Label Studio JSON export to LayoutXLM token-classification JSONL dataset.

Usage:
    python export_labelstudio_to_layoutxlm.py \
        --input labelstudio_export.json \
        --out_train datasets/train.jsonl \
        --out_val datasets/val.jsonl \
        --tokens_dir data/ocr_tokens \
        --split_ratio 0.9

The converter:
- Maps Label Studio rectangle annotations to OCR word indices via IoU/center-point matching
- Assigns BIO labels with priority resolution (CNIC > AMOUNT > DATE > ...)
- Validates alignment (words.length == bboxes.length == labels.length)
- Splits into train/val sets
"""
import argparse
import json
import os
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import warnings


# Label priority order (higher priority wins in overlaps)
LABEL_PRIORITY = {
    "CNIC": 7,
    "AMOUNT": 6,
    "DATE": 5,
    "REGISTRY_NO": 4,
    "PLOT_NO": 3,
    "SCHEME_NAME": 2,
    "PERSON_NAME": 1,
}

VALID_LABELS = ["PERSON_NAME", "CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT"]


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """Compute Intersection over Union (IoU) of two boxes.
    
    Args:
        box1: [x0, y0, x1, y1] in normalized coordinates
        box2: [x0, y0, x1, y1] in normalized coordinates
        
    Returns:
        IoU value between 0 and 1
    """
    x0_1, y0_1, x1_1, y1_1 = box1
    x0_2, y0_2, x1_2, y1_2 = box2
    
    # Intersection
    x0_i = max(x0_1, x0_2)
    y0_i = max(y0_1, y0_2)
    x1_i = min(x1_1, x1_2)
    y1_i = min(y1_1, y1_2)
    
    if x1_i <= x0_i or y1_i <= y0_i:
        return 0.0
    
    intersection = (x1_i - x0_i) * (y1_i - y0_i)
    
    # Union
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


def point_in_box(point: Tuple[float, float], box: List[float]) -> bool:
    """Check if point (x, y) is inside box [x0, y0, x1, y1]."""
    x, y = point
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1


def get_box_center(box: List[float]) -> Tuple[float, float]:
    """Get center point of box [x0, y0, x1, y1]."""
    x0, y0, x1, y1 = box
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def sort_boxes_by_reading_order(words: List[str], bboxes: List[List[float]]) -> List[int]:
    """Sort word indices by reading order (top-to-bottom, left-to-right).
    
    Args:
        words: List of words
        bboxes: List of bounding boxes
        
    Returns:
        List of indices sorted by reading order
    """
    if not words or not bboxes:
        return []
    
    # Create list of (index, bbox) tuples
    indexed = [(i, bbox) for i, bbox in enumerate(bboxes)]
    
    # Sort by y0 (top-to-bottom), then by x0 (left-to-right)
    sorted_indices = sorted(indexed, key=lambda x: (x[1][1], x[1][0]))
    
    return [idx for idx, _ in sorted_indices]


def match_annotation_to_words(
    annotation_box: List[float],
    word_bboxes: List[List[float]],
    iou_threshold: float = 0.3
) -> List[int]:
    """Match an annotation rectangle to word indices.
    
    Uses IoU overlap (>= threshold) OR center-point inclusion.
    
    Args:
        annotation_box: [x0, y0, x1, y1] in normalized coordinates
        word_bboxes: List of word bounding boxes
        iou_threshold: Minimum IoU for matching (default: 0.3)
        
    Returns:
        List of word indices that match the annotation
    """
    matches = []
    
    # Try IoU first
    for i, word_box in enumerate(word_bboxes):
        iou = compute_iou(annotation_box, word_box)
        if iou >= iou_threshold:
            matches.append(i)
    
    # If no IoU matches, try center-point inclusion
    if not matches:
        ann_center = get_box_center(annotation_box)
        for i, word_box in enumerate(word_bboxes):
            if point_in_box(ann_center, word_box):
                matches.append(i)
    
    # If still no matches, try word center-point inside annotation
    if not matches:
        for i, word_box in enumerate(word_bboxes):
            word_center = get_box_center(word_box)
            if point_in_box(word_center, annotation_box):
                matches.append(i)
    
    return matches


def assign_bio_labels(
    words: List[str],
    word_bboxes: List[List[float]],
    annotations: List[Dict[str, Any]]
) -> List[str]:
    """
    Assign BIO labels to words based on annotations with priority resolution.
    
    Args:
        words: List of OCR words
        word_bboxes: List of word bounding boxes (normalized 0-1000)
        annotations: List of annotation dicts with keys: 'value' (label), 'x', 'y', 'width', 'height'
        
    Returns:
        List of BIO labels aligned to words
    """
    # Initialize all labels as "O"
    labels = ["O"] * len(words)
    
    # Sort words by reading order
    reading_order = sort_boxes_by_reading_order(words, word_bboxes)
    
    # Extract annotation boxes with labels
    annotation_data = []
    
    for ann in annotations:
        # Label Studio format: value contains the annotation data
        value = ann.get("value", {})
        
        # Extract label
        if isinstance(value, dict):
            # Try different possible formats
            label = value.get("rectanglelabels", [None])
            if isinstance(label, list) and label:
                label = label[0]
            else:
                label = value.get("label") or (value.get("labels", [None])[0] if isinstance(value.get("labels"), list) else None)
        else:
            label = value
        
        if not label or label not in VALID_LABELS:
            continue
        
        # Extract bounding box coordinates
        # Label Studio format: x, y, width, height are percentages (0-100)
        x_percent = value.get("x", 0) if isinstance(value, dict) else ann.get("x", 0)
        y_percent = value.get("y", 0) if isinstance(value, dict) else ann.get("y", 0)
        width_percent = value.get("width", 0) if isinstance(value, dict) else ann.get("width", 0)
        height_percent = value.get("height", 0) if isinstance(value, dict) else ann.get("height", 0)
        
        # Convert percentages (0-100) to normalized 0-1000 coordinates
        x = x_percent * 10
        y = y_percent * 10
        width = width_percent * 10
        height = height_percent * 10
        
        ann_box = [x, y, x + width, y + height]
        annotation_data.append((label, ann_box, LABEL_PRIORITY.get(label, 0)))
    
    # Sort annotations by priority (highest first) to handle overlaps
    annotation_data.sort(key=lambda x: x[2], reverse=True)
    
    # Map each annotation to word indices
    for label, ann_box, priority in annotation_data:
        # Match to words
        word_indices = match_annotation_to_words(ann_box, word_bboxes)
        
        if not word_indices:
            continue
        
        # Sort matched indices by reading order
        word_indices = sorted(word_indices, key=lambda i: reading_order.index(i) if i in reading_order else len(reading_order))
        
        # Assign BIO labels (only if current label has higher priority or word is unlabeled)
        for idx, word_idx in enumerate(word_indices):
            current_label = labels[word_idx]
            current_base = current_label.replace("B-", "").replace("I-", "")
            current_priority = LABEL_PRIORITY.get(current_base, 0)
            
            if current_label == "O" or priority > current_priority:
                if idx == 0:
                    labels[word_idx] = f"B-{label}"
                else:
                    labels[word_idx] = f"I-{label}"
    
    return labels


def load_ocr_tokens(tokens_path: Path) -> Optional[Dict[str, Any]]:
    """Load OCR tokens from JSON file.
    
    Expected format:
    {
        "words": [...],
        "bboxes_norm_1000": [...]
    }
    """
    if not tokens_path.exists():
        return None
    
    try:
        with open(tokens_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        warnings.warn(f"Failed to load OCR tokens from {tokens_path}: {e}")
        return None


def convert_labelstudio_task(
    task: Dict[str, Any],
    tokens_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Convert a single Label Studio task to dataset format.
    
    Args:
        task: Label Studio task dict
        tokens_dir: Optional directory containing OCR token JSON files
        
    Returns:
        Dataset entry dict or None if conversion fails
    """
    # Extract task ID
    task_id = task.get("id")
    if not task_id:
        return None
    
    # Extract image path/URL
    data = task.get("data", {})
    image_path = data.get("image") or data.get("ocr")
    
    if not image_path:
        warnings.warn(f"Task {task_id}: No image path found")
        return None
    
    # Extract OCR tokens
    words = None
    bboxes_norm_1000 = None
    
    # Try from Label Studio data
    if "ocr" in data and isinstance(data["ocr"], dict):
        words = data["ocr"].get("words", [])
        bboxes = data["ocr"].get("boxes", [])
        if bboxes:
            # Convert boxes to normalized 0-1000 if needed
            # Assume boxes are already in normalized format or convert from pixels
            # This is a simplification; adjust based on actual Label Studio OCR format
            bboxes_norm_1000 = bboxes
    
    # Try from sidecar OCR file
    if (not words or not bboxes_norm_1000) and tokens_dir:
        # Construct tokens file path (assuming naming convention: task_id_tokens.json or similar)
        tokens_path = tokens_dir / f"{task_id}_tokens.json"
        ocr_data = load_ocr_tokens(tokens_path)
        if ocr_data:
            words = ocr_data.get("words", words)
            bboxes_norm_1000 = ocr_data.get("bboxes_norm_1000", bboxes_norm_1000)
    
    if not words or not bboxes_norm_1000:
        warnings.warn(f"Task {task_id}: No OCR tokens found")
        return None
    
    if len(words) != len(bboxes_norm_1000):
        warnings.warn(f"Task {task_id}: Mismatch: {len(words)} words but {len(bboxes_norm_1000)} boxes")
        return None
    
    # Extract annotations
    annotations = task.get("annotations", [])
    if not annotations:
        # Unlabeled task - assign all "O"
        labels = ["O"] * len(words)
    else:
        # Use first annotation (or merge multiple if needed)
        annotation = annotations[0]
        result = annotation.get("result", [])
        labels = assign_bio_labels(words, bboxes_norm_1000, result)
    
    # Validate labels
    valid_labels = set(["O"] + [f"{prefix}-{label}" for prefix in ["B", "I"] for label in VALID_LABELS])
    if any(label not in valid_labels for label in labels):
        warnings.warn(f"Task {task_id}: Invalid labels found")
        return None
    
    # Construct output entry
    entry = {
        "id": str(task_id),
        "image_path": image_path,
        "words": words,
        "bboxes_norm_1000": bboxes_norm_1000,
        "labels": labels,
    }
    
    return entry


def main():
    parser = argparse.ArgumentParser(description="Convert Label Studio export to LayoutXLM JSONL dataset")
    parser.add_argument("--input", required=True, help="Input Label Studio JSON export file")
    parser.add_argument("--out_train", required=True, help="Output training JSONL file")
    parser.add_argument("--out_val", required=True, help="Output validation JSONL file")
    parser.add_argument("--tokens_dir", help="Directory containing OCR token JSON files (sidecar)")
    parser.add_argument("--split_ratio", type=float, default=0.9, help="Train/val split ratio (default: 0.9)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    
    args = parser.parse_args()
    
    # Load Label Studio export
    print(f"Loading Label Studio export from: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        ls_data = json.load(f)
    
    tasks = ls_data if isinstance(ls_data, list) else ls_data.get("tasks", [])
    print(f"Found {len(tasks)} tasks")
    
    # Convert tasks
    tokens_dir = Path(args.tokens_dir) if args.tokens_dir else None
    
    converted = []
    skipped = []
    
    for task in tasks:
        entry = convert_labelstudio_task(task, tokens_dir)
        if entry:
            converted.append(entry)
        else:
            skipped.append(task.get("id", "unknown"))
    
    print(f"Converted: {len(converted)} tasks")
    print(f"Skipped: {len(skipped)} tasks")
    if skipped:
        print(f"  Skipped IDs: {skipped[:10]}{'...' if len(skipped) > 10 else ''}")
    
    # Count labels
    label_counts = {}
    for entry in converted:
        for label in entry["labels"]:
            label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\nLabel counts:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    
    # Split into train/val
    random.seed(args.seed)
    random.shuffle(converted)
    
    split_idx = int(len(converted) * args.split_ratio)
    train_data = converted[:split_idx]
    val_data = converted[split_idx:]
    
    print(f"\nSplit: {len(train_data)} train, {len(val_data)} val")
    
    # Write output files
    print(f"Writing training data to: {args.out_train}")
    os.makedirs(os.path.dirname(args.out_train) or '.', exist_ok=True)
    with open(args.out_train, 'w', encoding='utf-8') as f:
        for entry in train_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"Writing validation data to: {args.out_val}")
    os.makedirs(os.path.dirname(args.out_val) or '.', exist_ok=True)
    with open(args.out_val, 'w', encoding='utf-8') as f:
        for entry in val_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print("\nConversion complete!")


if __name__ == "__main__":
    main()

