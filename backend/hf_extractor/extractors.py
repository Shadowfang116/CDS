"""Token-based entity extractors for OCR text (no ML, strict token assembly)."""
import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedEntityData:
    """Internal structure for extracted entity."""
    label: str
    value: str
    confidence: float
    token_indices: List[int]
    bbox: Optional[List[float]] = None  # Pixel coordinates [x1, y1, x2, y2] (None for text-only OCR)
    bbox_norm_1000: Optional[List[int]] = None  # Normalized to 0-1000 scale [x1, y1, x2, y2] (None if no bbox)
    span_start: Optional[int] = None  # Character offset start in page text (for text-only OCR)
    span_end: Optional[int] = None  # Character offset end in page text (for text-only OCR)


def _normalize_bbox_to_1000(bbox: List[float], image_width: float, image_height: float) -> List[int]:
    """
    Normalize bbox from pixel coordinates to 0-1000 scale.
    
    Args:
        bbox: [x1, y1, x2, y2] in pixel coordinates
        image_width: Image width in pixels
        image_height: Image height in pixels
        
    Returns:
        Normalized bbox as [x1, y1, x2, y2] scaled to 0-1000
    """
    if len(bbox) < 4 or image_width <= 0 or image_height <= 0:
        return [0, 0, 0, 0]
    
    scale_x = 1000.0 / image_width
    scale_y = 1000.0 / image_height
    
    return [
        int(bbox[0] * scale_x),
        int(bbox[1] * scale_y),
        int(bbox[2] * scale_x),
        int(bbox[3] * scale_y),
    ]


def _compute_bbox_union(boxes: Optional[List[List[float]]], indices: List[int]) -> Optional[List[float]]:
    """Compute union bounding box from token boxes at given indices.
    
    Returns None if boxes are None (text-only OCR).
    """
    if not indices or not boxes:
        return None
    
    selected_boxes = [boxes[i] for i in indices if i < len(boxes)]
    if not selected_boxes:
        return None
    
    min_x1 = min(box[0] for box in selected_boxes)
    min_y1 = min(box[1] for box in selected_boxes)
    max_x2 = max(box[2] for box in selected_boxes)
    max_y2 = max(box[3] for box in selected_boxes)
    
    return [min_x1, min_y1, max_x2, max_y2]


def _compute_span_offsets(words: List[str], token_indices: List[int]) -> Tuple[Optional[int], Optional[int]]:
    """
    Compute character span offsets for token indices in page text.
    
    Args:
        words: List of OCR words
        token_indices: List of token indices
        
    Returns:
        Tuple of (span_start, span_end) character offsets in joined page text.
        Returns (None, None) if indices are empty or invalid.
    """
    if not token_indices or not words:
        return None, None
    
    # Build page text: join words with spaces
    page_text = " ".join(words)
    
    # Find first and last token indices
    first_idx = min(token_indices)
    last_idx = max(token_indices)
    
    # Compute character positions: iterate through words and track position
    char_pos = 0
    span_start = None
    span_end = None
    
    for i, word in enumerate(words):
        if i == first_idx:
            span_start = char_pos
        if i == last_idx:
            span_end = char_pos + len(word)
            break
        char_pos += len(word) + 1  # +1 for space after word
    
    # Fallback: if indices not found
    if span_start is None:
        span_start = 0
    if span_end is None:
        span_end = len(page_text)
    
    return span_start, span_end


def _get_snippet(words: List[str], indices: List[int], window: int = 5) -> str:
    """Get snippet by joining tokens in a window around the extracted span."""
    if not indices:
        return ""
    
    min_idx = max(0, min(indices) - window)
    max_idx = min(len(words), max(indices) + 1 + window)
    
    snippet_tokens = words[min_idx:max_idx]
    snippet = " ".join(snippet_tokens)
    
    # Truncate to reasonable length
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    
    return snippet


def _is_mojibake_or_corrupted(token: str) -> bool:
    """Check if token looks corrupted (box drawing chars, etc.)."""
    if not token:
        return True
    
    # Check for box drawing characters (common OCR errors)
    box_chars = ['─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '═', '║', '╔', '╗', '╚', '╝']
    if any(char in token for char in box_chars):
        return True
    
    # Check if token is mostly non-printable or control characters
    if len(token) > 0:
        printable_ratio = sum(1 for c in token if c.isprintable()) / len(token)
        if printable_ratio < 0.5:
            return True
    
    return False


def extract_plot_number(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract plot number using anchor-based detection.
    
    Detects anchors like "plot", "no", "plot#", "پلاٹ", "نمبر" and captures
    following tokens that look like plot identifiers.
    """
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # English anchors (case-insensitive)
    plot_anchors_en = [
        ["plot", "no"],
        ["plot", "number"],
        ["plot", "#"],
        ["plot"],
        ["commercial", "plot"],
    ]
    
    # Urdu anchors (پلاٹ = plot, نمبر = number)
    plot_anchors_urdu = [
        ["پلاٹ", "نمبر"],
        ["پلاٹ"],
    ]
    
    # Pattern for plot number: digits, alnum with hyphens, or like "14-A", "Com-14"
    plot_pattern = re.compile(r'^[\dA-Za-z\-/]+$')
    plot_digit_pattern = re.compile(r'^\d+[\-A-Za-z/]*$')
    
    i = 0
    while i < len(words):
        word_lower = words[i].lower().strip()
        
        # Check English anchors
        for anchor_seq in plot_anchors_en:
            if i + len(anchor_seq) > len(words):
                continue
            
            # Check if anchor sequence matches
            matches = True
            for j, anchor_token in enumerate(anchor_seq):
                if i + j >= len(words):
                    matches = False
                    break
                if words[i + j].lower().strip() != anchor_token:
                    matches = False
                    break
            
            if matches:
                # Found anchor, look for plot number in next 1-3 tokens
                search_start = i + len(anchor_seq)
                search_end = min(len(words), search_start + 3)
                
                for j in range(search_start, search_end):
                    token = words[j].strip()
                    if _is_mojibake_or_corrupted(token):
                        continue
                    
                    # Check if token looks like a plot number
                    if plot_digit_pattern.match(token) or plot_pattern.match(token):
                        # Found plot number
                        token_indices = [j]
                        value = token
                        
                        # Try to extend if next token looks like part of plot (e.g., "14-A")
                        if j + 1 < len(words):
                            next_token = words[j + 1].strip()
                            if re.match(r'^[A-Za-z\-/]+$', next_token) and len(next_token) <= 5:
                                token_indices.append(j + 1)
                                value = f"{token}-{next_token}"
                        
                        confidence = 0.85 if len(anchor_seq) >= 2 else 0.70
                        bbox = _compute_bbox_union(boxes, token_indices)
                        span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
                        
                        entities.append(ExtractedEntityData(
                            label="PLOT_NO",
                            value=value,
                            confidence=confidence,
                            token_indices=token_indices,
                            bbox=bbox,
                            span_start=span_start,
                            span_end=span_end,
                        ))
                        break  # Only first match per anchor
                
                i += len(anchor_seq)
                continue
        
        # Check Urdu anchors
        for anchor_seq in plot_anchors_urdu:
            if i + len(anchor_seq) > len(words):
                continue
            
            matches = True
            for j, anchor_token in enumerate(anchor_seq):
                if i + j >= len(words):
                    matches = False
                    break
                if words[i + j].strip() != anchor_token:
                    matches = False
                    break
            
            if matches:
                search_start = i + len(anchor_seq)
                search_end = min(len(words), search_start + 3)
                
                for j in range(search_start, search_end):
                    token = words[j].strip()
                    if _is_mojibake_or_corrupted(token):
                        continue
                    
                    if plot_digit_pattern.match(token) or plot_pattern.match(token):
                        token_indices = [j]
                        value = token
                        
                        if j + 1 < len(words):
                            next_token = words[j + 1].strip()
                            if re.match(r'^[A-Za-z\-/]+$', next_token) and len(next_token) <= 5:
                                token_indices.append(j + 1)
                                value = f"{token}-{next_token}"
                        
                        confidence = 0.85
                        bbox = _compute_bbox_union(boxes, token_indices)
                        span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
                        
                        entities.append(ExtractedEntityData(
                            label="PLOT_NO",
                            value=value,
                            confidence=confidence,
                            token_indices=token_indices,
                            bbox=bbox,
                            span_start=span_start,
                            span_end=span_end,
                        ))
                        break
                
                i += len(anchor_seq)
                continue
        
        i += 1
    
    return entities


def extract_scheme_name(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract scheme/society name using suffix patterns.
    
    Detects patterns ending with "Housing Scheme", "Society", "Town", etc.
    and captures preceding title-like span.
    """
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # Suffix patterns (case-insensitive)
    suffixes = [
        "housing scheme",
        "society",
        "town",
        "city",
        "scheme",
        "cooperative society",
    ]
    
    text_lower = " ".join([w.lower() for w in words])
    
    for suffix in suffixes:
        pattern = r'\b' + re.escape(suffix) + r'\b'
        matches = list(re.finditer(pattern, text_lower))
        
        for match in matches:
            # Find word indices for this match
            # Count characters up to match position
            char_pos = match.start()
            suffix_start_idx = 0
            char_count = 0
            
            for idx, word in enumerate(words):
                if char_count >= char_pos:
                    suffix_start_idx = idx
                    break
                char_count += len(word) + 1  # +1 for space
            
            if suffix_start_idx == 0:
                continue
            
            # Extract preceding span (2-8 tokens before suffix)
            span_start = max(0, suffix_start_idx - 8)
            span_end = suffix_start_idx
            
            span_tokens = words[span_start:span_end]
            span_indices = list(range(span_start, span_end))
            
            # Filter out corrupted tokens
            clean_tokens = []
            clean_indices = []
            for token, idx in zip(span_tokens, span_indices):
                if not _is_mojibake_or_corrupted(token):
                    clean_tokens.append(token)
                    clean_indices.append(idx)
            
            if not clean_tokens:
                continue
            
            # Reject if contains sentence punctuation or too long
            value = " ".join(clean_tokens)
            if len(clean_tokens) > 8:
                continue
            
            # Check for sentence-ending punctuation (reject if found)
            if re.search(r'[.!?]$', value):
                continue
            
            # Must start with capital letter or be all caps (title-like)
            first_char = clean_tokens[0][0] if clean_tokens[0] else ""
            if not (first_char.isupper() or clean_tokens[0].isupper()):
                continue
            
            confidence = 0.75
            bbox = _compute_bbox_union(boxes, clean_indices)
            span_start, span_end = _compute_span_offsets(words, clean_indices) if boxes is None else (None, None)
            
            entities.append(ExtractedEntityData(
                label="SCHEME_NAME",
                value=value.strip(),
                confidence=confidence,
                token_indices=clean_indices,
                bbox=bbox,
                span_start=span_start,
                span_end=span_end,
            ))
            break  # Only first match per suffix type
    
    return entities


def extract_registry_number(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract registry/document number using anchor detection."""
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # English anchors
    anchors_en = [
        "reg",
        "reg.",
        "registration",
        "registry",
        "instrument",
        "doc no",
        "deed no",
        "document no",
    ]
    
    # Urdu anchors: "رجسٹری" = registry, "رجسٹری نمبر" = registry number
    anchors_urdu = [
        "رجسٹری نمبر",
        "رجسٹری",
    ]
    
    # Pattern for registry number: digits with possible "/", "-"
    reg_pattern = re.compile(r'^[\d\-/]+$')
    
    i = 0
    while i < len(words):
        # Check English anchors (single word or two-word)
        for anchor in anchors_en:
            anchor_tokens = anchor.split()
            if i + len(anchor_tokens) > len(words):
                continue
            
            matches = True
            for j, anchor_token in enumerate(anchor_tokens):
                if words[i + j].lower().strip() != anchor_token:
                    matches = False
                    break
            
            if matches:
                # Look for number in next 1-3 tokens
                search_start = i + len(anchor_tokens)
                search_end = min(len(words), search_start + 3)
                
                for j in range(search_start, search_end):
                    token = words[j].strip()
                    if _is_mojibake_or_corrupted(token):
                        continue
                    
                    if reg_pattern.match(token):
                        token_indices = [j]
                        value = token
                        confidence = 0.80
                        bbox = _compute_bbox_union(boxes, token_indices)
                        span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
                        
                        entities.append(ExtractedEntityData(
                            label="REGISTRY_NO",
                            value=value,
                            confidence=confidence,
                            token_indices=token_indices,
                            bbox=bbox,
                            span_start=span_start,
                            span_end=span_end,
                        ))
                        break
                
                i += len(anchor_tokens)
                continue
        
        # Check Urdu anchors
        for anchor in anchors_urdu:
            anchor_tokens = anchor.split()
            if i + len(anchor_tokens) > len(words):
                continue
            
            matches = True
            for j, anchor_token in enumerate(anchor_tokens):
                if words[i + j].strip() != anchor_token:
                    matches = False
                    break
            
            if matches:
                search_start = i + len(anchor_tokens)
                search_end = min(len(words), search_start + 3)
                
                for j in range(search_start, search_end):
                    token = words[j].strip()
                    if _is_mojibake_or_corrupted(token):
                        continue
                    
                    if reg_pattern.match(token):
                        token_indices = [j]
                        value = token
                        confidence = 0.80
                        bbox = _compute_bbox_union(boxes, token_indices)
                        span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
                        
                        entities.append(ExtractedEntityData(
                            label="REGISTRY_NO",
                            value=value,
                            confidence=confidence,
                            token_indices=token_indices,
                            bbox=bbox,
                            span_start=span_start,
                            span_end=span_end,
                        ))
                        break
                
                i += len(anchor_tokens)
                continue
        
        i += 1
    
    return entities


def extract_date(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract dates from tokens."""
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # Date patterns
    # dd/mm/yyyy, dd-mm-yyyy
    numeric_pattern = re.compile(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$')
    # yyyy-mm-dd
    iso_pattern = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')
    # Month name patterns: "Jan 15, 2024", "January 15, 2024"
    month_pattern = re.compile(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}$', re.IGNORECASE)
    
    i = 0
    while i < len(words):
        token = words[i].strip()
        
        if _is_mojibake_or_corrupted(token):
            i += 1
            continue
        
        # Check numeric formats (single token)
        if numeric_pattern.match(token) or iso_pattern.match(token):
            token_indices = [i]
            value = token
            confidence = 0.80
            bbox = _compute_bbox_union(boxes, token_indices)
            span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
            
            entities.append(ExtractedEntityData(
                label="DATE",
                value=value,
                confidence=confidence,
                token_indices=token_indices,
                bbox=bbox,
                span_start=span_start,
                span_end=span_end,
            ))
            i += 1
            continue
        
        # Check month name pattern (may span 2-3 tokens)
        if i + 2 < len(words):
            span_2 = " ".join(words[i:i+2])
            span_3 = " ".join(words[i:i+3])
            
            if month_pattern.match(span_2):
                token_indices = [i, i+1]
                value = span_2
                confidence = 0.70
                bbox = _compute_bbox_union(boxes, token_indices)
                
                entities.append(ExtractedEntityData(
                    label="DATE",
                    value=value,
                    confidence=confidence,
                    token_indices=token_indices,
                    bbox=bbox,
                ))
                i += 2
                continue
            
            if month_pattern.match(span_3):
                token_indices = [i, i+1, i+2]
                value = span_3
                confidence = 0.70
                bbox = _compute_bbox_union(boxes, token_indices)
                
                entities.append(ExtractedEntityData(
                    label="DATE",
                    value=value,
                    confidence=confidence,
                    token_indices=token_indices,
                    bbox=bbox,
                ))
                i += 3
                continue
        
        i += 1
    
    return entities


def extract_amount(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract amount/consideration using currency anchors."""
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # Currency anchors
    currency_anchors = [
        "rs",
        "rs.",
        "pkr",
        "rupees",
        "rupee",
        "₨",
        "consideration",
    ]
    
    # Pattern for amount: digits with commas (e.g., "15,600,000")
    amount_pattern = re.compile(r'^[\d,]+(?:\.\d+)?$')
    
    i = 0
    while i < len(words):
        word_lower = words[i].lower().strip()
        
        # Check if current word is a currency anchor
        is_anchor = False
        anchor_confidence = 0.85
        
        if word_lower in currency_anchors:
            is_anchor = True
            if word_lower == "consideration":
                anchor_confidence = 0.75
        elif i + 1 < len(words):
            # Check two-word anchors like "Rs.", "PKR"
            two_word = f"{word_lower} {words[i+1].lower().strip()}"
            if two_word in currency_anchors:
                is_anchor = True
                i += 1  # Skip next word too
        
        if is_anchor:
            # Look for amount in next 1-6 tokens
            search_start = i + 1
            search_end = min(len(words), search_start + 6)
            
            for j in range(search_start, search_end):
                token = words[j].strip()
                if _is_mojibake_or_corrupted(token):
                    continue
                
                # Remove common punctuation/suffixes
                clean_token = token.rstrip('.,;:')
                
                if amount_pattern.match(clean_token):
                    token_indices = [j]
                    value = clean_token
                    confidence = anchor_confidence
                    bbox = _compute_bbox_union(boxes, token_indices)
                    span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
                    
                    entities.append(ExtractedEntityData(
                        label="AMOUNT",
                        value=value,
                        confidence=confidence,
                        token_indices=token_indices,
                        bbox=bbox,
                        span_start=span_start,
                        span_end=span_end,
                    ))
                    break  # Only first match per anchor
        
        i += 1
    
    return entities


def extract_cnic(words: List[str], boxes: Optional[List[List[float]]] = None) -> List[ExtractedEntityData]:
    """Extract CNIC using existing logic (simplified version from main.py)."""
    entities = []
    
    # P12: Handle text-only OCR (boxes=None)
    if boxes is not None and len(words) != len(boxes):
        return entities
    
    # Pakistani CNIC patterns
    cnic_pattern_with_hyphens = re.compile(r'\b\d{5}-\d{7}-\d\b')
    cnic_pattern_digits_only = re.compile(r'\b\d{13}\b')
    
    for i, word in enumerate(words):
        if _is_mojibake_or_corrupted(word):
            continue
        
        # Check for exact match with hyphens
        match = cnic_pattern_with_hyphens.search(word)
        if match:
            matched_text = match.group()
            token_indices = [i]
            value = words[i]  # Use original word from OCR
            confidence = 0.95
            bbox = _compute_bbox_union(boxes, token_indices)
            span_start, span_end = _compute_span_offsets(words, token_indices) if boxes is None else (None, None)
            
            entities.append(ExtractedEntityData(
                label="CNIC",
                value=value,
                confidence=confidence,
                token_indices=token_indices,
                bbox=bbox,
                span_start=span_start,
                span_end=span_end,
            ))
            continue
        
        # Check for 13-digit pattern
        match = cnic_pattern_digits_only.search(word)
        if match:
            digits = match.group()
            if len(digits) == 13:
                token_indices = [i]
                value = words[i]  # Use original word from OCR
                confidence = 0.95
                bbox = _compute_bbox_union(boxes, token_indices)
                
                entities.append(ExtractedEntityData(
                    label="CNIC",
                    value=value,
                    confidence=confidence,
                    token_indices=token_indices,
                    bbox=bbox,
                ))
    
    return entities


def extract_all_entities(
    words: List[str],
    boxes: Optional[List[List[float]]] = None,
    labels: Optional[List[str]] = None,
    image_width: float = 1000.0,
    image_height: float = 1000.0,
) -> List[ExtractedEntityData]:
    """Extract all entities using token-based extractors.
    
    Args:
        words: List of OCR words
        boxes: List of bounding boxes [x1, y1, x2, y2] for each word (pixel coordinates)
        labels: Optional list of labels to extract. If None, extracts all.
        image_width: Image width in pixels (for bbox normalization)
        image_height: Image height in pixels (for bbox normalization)
    
    Returns:
        List of extracted entities with bbox_norm_1000 included
    """
    all_entities = []
    
    if labels is None:
        labels = ["CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT"]
    
    extractors = {
        "CNIC": extract_cnic,
        "PLOT_NO": extract_plot_number,
        "SCHEME_NAME": extract_scheme_name,
        "REGISTRY_NO": extract_registry_number,
        "DATE": extract_date,
        "AMOUNT": extract_amount,
    }
    
    for label in labels:
        if label in extractors:
            entities = extractors[label](words, boxes)
            # Add bbox_norm_1000 to each entity (only if bbox exists)
            for entity in entities:
                if entity.bbox is not None and entity.bbox_norm_1000 is None:
                    entity.bbox_norm_1000 = _normalize_bbox_to_1000(
                        entity.bbox,
                        image_width,
                        image_height
                    )
            all_entities.extend(entities)
    
    return all_entities

