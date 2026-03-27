"""Phase 6: Layout-aware OCR segmentation for scanned legal documents."""
import logging
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image

from app.services.ocr_preprocess import pil_to_cv, cv_to_pil

logger = logging.getLogger(__name__)


def downscale_for_layout(img_cv:
    np.ndarray, max_side: int) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Downscale image for faster segmentation while preserving aspect ratio.
    
    Args:
        img_cv: OpenCV image array
        max_side: Maximum side length
    
    Returns:
        Tuple of (downscaled_image, scale_dict with sx, sy)
    """
    h, w = img_cv.shape[:2]
    max_dim = max(h, w)
    
    if max_dim <= max_side:
        return img_cv, {"sx": 1.0, "sy": 1.0}
    
    scale = max_side / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    downscaled = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return downscaled, {"sx": scale, "sy": scale}


def find_text_mask(gray:
    np.ndarray) -> np.ndarray:
    """
    Find text mask using adaptive threshold or Otsu.
    
    Args:
        gray: Grayscale image array
    
    Returns:
        Binary mask (text = white, background = black)
    """
    try:
        # Use adaptive threshold for better results on varying backgrounds
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # Invert so text is white on black background for morphology
        return binary
        
    except Exception as e:
        logger.warning(f"Adaptive threshold failed: {e}, trying Otsu")
        try:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            return binary
        except Exception as e2:
            logger.error(f"Otsu threshold failed: {e2}")
            # Fallback: simple threshold
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            return binary


def detect_blocks(mask:
    np.ndarray, min_area_pct: float, max_blocks: int) -> List[Dict[str, int]]:
    """
    Detect text blocks from binary mask using morphological operations and contours.
    
    Args:
        mask: Binary mask (text = white, background = black)
        min_area_pct: Minimum block area as percentage of page area
        max_blocks: Maximum number of blocks to return
    
    Returns:
        List of block dicts with x, y, w, h, area
    """
    h, w = mask.shape
    page_area = h * w
    min_area = int(page_area * min_area_pct)
    
    try:
        # Morphological close to connect letters into lines/blocks
        # Use rectangular kernel: wider than tall to connect horizontally
        kernel_w = max(5, int(w * 0.01))  # ~1% of width
        kernel_h = max(3, int(h * 0.005))  # ~0.5% of height
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, kernel_h))
        
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Extract bounding boxes
        boxes = []
        for contour in contours:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            area = w_box * h_box
            
            # Filter by minimum area
            if area >= min_area:
                boxes.append({
                    "x": int(x),
                    "y": int(y),
                    "w": int(w_box),
                    "h": int(h_box),
                    "area": int(area),
                })
        
        # Sort by area descending and keep top max_blocks
        boxes.sort(key=lambda b: b["area"], reverse=True)
        boxes = boxes[:max_blocks]
        
        return boxes
        
    except Exception as e:
        logger.error(f"Block detection failed: {e}")
        return []


def merge_boxes(boxes:
    List[Dict[str, int]], y_gap_px: int) -> List[Dict[str, int]]:
    """
    Merge boxes that are close vertically (same line/block).
    
    Args:
        boxes: List of box dicts with x, y, w, h
        y_gap_px: Maximum Y gap for merging
    
    Returns:
        List of merged boxes
    """
    if not boxes:
        return []
    
    # Sort by y then x
    sorted_boxes = sorted(boxes, key=lambda b: (b["y"], b["x"]))
    
    merged = []
    current_group = [sorted_boxes[0]]
    
    for box in sorted_boxes[1:]:
        # Check if box overlaps or is close to any box in current group
        should_merge = False
        
        for group_box in current_group:
            # Calculate Y overlap
            y1_max = max(group_box["y"], box["y"])
            y2_min = min(group_box["y"] + group_box["h"], box["y"] + box["h"])
            y_overlap = max(0, y2_min - y1_max)
            
            # Calculate Y gap
            y_gap = min(
                abs(box["y"] - (group_box["y"] + group_box["h"])),
                abs(group_box["y"] - (box["y"] + box["h"]))
            )
            
            # Merge if overlap exists or gap is small
            if y_overlap > 0 or y_gap <= y_gap_px:
                should_merge = True
                break
        
        if should_merge:
            current_group.append(box)
        else:
            # Merge current group into one box
            if current_group:
                merged_box = merge_box_group(current_group)
                merged.append(merged_box)
            current_group = [box]
    
    # Merge last group
    if current_group:
        merged_box = merge_box_group(current_group)
        merged.append(merged_box)
    
    return merged


def merge_box_group(boxes:
    List[Dict[str, int]]) -> Dict[str, int]:
    """Merge a group of boxes into a single bounding box."""
    if not boxes:
        return {"x": 0, "y": 0, "w": 0, "h": 0, "area": 0}
    
    if len(boxes) == 1:
        return boxes[0].copy()
    
    x_min = min(b["x"] for b in boxes)
    y_min = min(b["y"] for b in boxes)
    x_max = max(b["x"] + b["w"] for b in boxes)
    y_max = max(b["y"] + b["h"] for b in boxes)
    
    return {
        "x": x_min,
        "y": y_min,
        "w": x_max - x_min,
        "h": y_max - y_min,
        "area": (x_max - x_min) * (y_max - y_min),
    }


def reading_order(boxes:
    List[Dict[str, int]], expected_script: str) -> List[Dict[str, int]]:
    """
    Sort boxes in reading order.
    
    For Urdu/RTL: sort x DESC within row
    For English/LTR: sort x ASC within row
    
    Args:
        boxes: List of box dicts with x, y, w, h
        expected_script: "urdu"|"english"|"mixed"|"unknown"
    
    Returns:
        List of boxes with added "row" field, sorted in reading order
    """
    if not boxes:
        return []
    
    # Group boxes by row using y-centroid tolerance
    # Tolerance: ~5% of average box height
    avg_height = sum(b["h"] for b in boxes) / len(boxes) if boxes else 0
    row_tolerance = max(10, int(avg_height * 0.05))
    
    # Assign row numbers
    rows = []
    for box in boxes:
        y_center = box["y"] + box["h"] // 2
        
        # Find matching row
        assigned = False
        for row_idx, row_boxes in enumerate(rows):
            # Check if y_center is within tolerance of any box in this row
            for row_box in row_boxes:
                row_y_center = row_box["y"] + row_box["h"] // 2
                if abs(y_center - row_y_center) <= row_tolerance:
                    rows[row_idx].append(box)
                    assigned = True
                    break
            if assigned:
                break
        
        if not assigned:
            rows.append([box])
    
    # Sort within each row based on script direction
    is_rtl = expected_script in ["urdu", "mixed"]
    
    ordered_boxes = []
    for row_idx, row_boxes in enumerate(rows):
        # Sort by x within row
        if is_rtl:
            # Right-to-left: sort x DESC
            row_boxes.sort(key=lambda b: b["x"], reverse=True)
        else:
            # Left-to-right: sort x ASC
            row_boxes.sort(key=lambda b: b["x"])
        
        # Add row number to each box
        for box in row_boxes:
            box_with_row = box.copy()
            box_with_row["row"] = row_idx
            ordered_boxes.append(box_with_row)
    
    # Sort rows by y
    ordered_boxes.sort(key=lambda b: (b["row"], b["y"]))
    
    return ordered_boxes


def segment_page(pil_img:
    Image.Image, *, expected_script: str, settings_obj) -> Dict[str, Any]:
    """
    Phase 6: Segment page into text blocks for layout-aware OCR.
    
    Args:
        pil_img: PIL Image to segment
        expected_script: "urdu"|"english"|"mixed"|"unknown"
        settings_obj: Settings object with layout config
    
    Returns:
        Dict with boxes, scale, mode, success, error
    """
    result: Dict[str, Any] = {
        "boxes": [],
        "scale": {"sx": 1.0, "sy": 1.0},
        "mode": settings_obj.OCR_LAYOUT_MODE,
        "success": False,
    }
    
    try:
        # Convert PIL to OpenCV
        img_cv = pil_to_cv(pil_img)
        original_h, original_w = img_cv.shape[:2]
        
        # Convert to grayscale if needed
        if len(img_cv.shape) == 3:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_cv
        
        # Downscale for faster segmentation
        gray_scaled, scale_info = downscale_for_layout(gray, settings_obj.OCR_LAYOUT_DOWNSCALE_MAX_SIDE)
        result["scale"] = scale_info
        
        # Find text mask
        mask = find_text_mask(gray_scaled)
        
        # Detect blocks
        boxes = detect_blocks(
            mask,
            min_area_pct=settings_obj.OCR_LAYOUT_MIN_BLOCK_AREA_PCT,
            max_blocks=settings_obj.OCR_LAYOUT_MAX_BLOCKS
        )
        
        if not boxes:
            result["error"] = "no_blocks_detected"
            return result
        
        # Merge close boxes
        boxes_merged = merge_boxes(boxes, settings_obj.OCR_LAYOUT_MERGE_Y_GAP_PX)
        
        # Scale boxes back to original image coordinates
        sx = scale_info["sx"]
        sy = scale_info["sy"]
        
        boxes_scaled = []
        for box in boxes_merged:
            boxes_scaled.append({
                "x": int(box["x"] / sx),
                "y": int(box["y"] / sy),
                "w": int(box["w"] / sx),
                "h": int(box["h"] / sy),
                "area": int(box["area"] / (sx * sy)),
            })
        
        # Sort in reading order
        boxes_ordered = reading_order(boxes_scaled, expected_script)
        
        result["boxes"] = boxes_ordered
        result["success"] = True
        
        return result
        
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"Layout segmentation failed: {error_msg}")
        result["error"] = error_msg
        return result

