"""Phase 4: Deterministic quality scoring for OCR output selection."""
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Unicode regex patterns
URDU_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
DIGIT_RE = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]")  # ASCII + Arabic-Indic + Extended Arabic-Indic digits
GARBAGE_RE = re.compile(r"[\uFFFDï¿½]")  # Replacement characters
WHITESPACE_RE = re.compile(r"[\s\n\n\t]")


def urdu_char_ratio(text:
    str) -> float:
    """Calculate ratio of Urdu/Arabic characters."""
    if not text:
        return 0.0
    matches = len(URDU_ARABIC_RE.findall(text))
    return matches / len(text)


def latin_ratio(text:
    str) -> float:
    """Calculate ratio of Latin (A-Za-z) characters."""
    if not text:
        return 0.0
    matches = len(LATIN_RE.findall(text))
    return matches / len(text)


def digit_ratio(text:
    str) -> float:
    """Calculate ratio of digits (ASCII + Urdu digits)."""
    if not text:
        return 0.0
    matches = len(DIGIT_RE.findall(text))
    return matches / len(text)


def garbage_ratio(text:
    str) -> float:
    """Calculate ratio of garbage/replacement characters."""
    if not text:
        return 0.0
    matches = len(GARBAGE_RE.findall(text))
    return matches / len(text)


def whitespace_ratio(text:
    str) -> float:
    """Calculate ratio of whitespace characters."""
    if not text:
        return 0.0
    matches = len(WHITESPACE_RE.findall(text))
    return matches / len(text)


def unique_char_ratio(text:
    str) -> float:
    """Calculate ratio of unique characters (diversity measure)."""
    if not text:
        return 0.0
    unique_chars = len(set(text))
    return unique_chars / len(text) if len(text) > 0 else 0.0


def score_text(text:
    str, *, expected_script: str, min_len: int) -> Dict[str, Any]:
    """
    Phase 4: Score OCR text quality deterministically.
    
    Args:
        text: OCR extracted text
        expected_script: "urdu"|"english"|"mixed"|"unknown"
        min_len: Minimum text length threshold
    
    Returns:
        Dict with "score" (float) and "metrics" (dict of ratios)
    """
    metrics: Dict[str, Any] = {}
    
    text_len = len(text)
    
    # Base score starts at 0
    base_score = 0.0
    
    # Check minimum length
    if text_len < min_len:
        base_score = -5.0  # Heavy penalty for too short
        metrics["length_penalty"] = True
    else:
        # Length score (logarithmic bonus)
        import math
        length_score = math.log10(max(1, text_len / min_len)) * 2.0
        base_score += length_score
        metrics["length_score"] = round(length_score, 2)
    
    # Calculate character ratios
    urdu_ratio = urdu_char_ratio(text)
    latin_ratio_val = latin_ratio(text)
    digit_ratio_val = digit_ratio(text)
    garbage_ratio_val = garbage_ratio(text)
    whitespace_ratio_val = whitespace_ratio(text)
    unique_ratio = unique_char_ratio(text)
    
    metrics.update({
        "urdu_ratio": round(urdu_ratio, 4),
        "latin_ratio": round(latin_ratio_val, 4),
        "digit_ratio": round(digit_ratio_val, 4),
        "garbage_ratio": round(garbage_ratio_val, 4),
        "whitespace_ratio": round(whitespace_ratio_val, 4),
        "unique_ratio": round(unique_ratio, 4),
        "text_length": text_len,
    })
    
    # Script match score
    script_match_score = 0.0
    if expected_script == "urdu":
        script_match_score = 2.0 * urdu_ratio
    elif expected_script == "english":
        script_match_score = 2.0 * latin_ratio_val
    elif expected_script == "mixed":
        script_match_score = 1.2 * (urdu_ratio + latin_ratio_val)
    else:  # unknown
        # For unknown, give bonus for having any script
        script_match_score = 1.0 * max(urdu_ratio, latin_ratio_val)
    
    base_score += script_match_score
    metrics["script_match_score"] = round(script_match_score, 2)
    
    # Structure score (bonus for newlines = document structure)
    newline_count = text.count('\n')
    if newline_count > 0:
        structure_bonus = min(1.0, newline_count / 10.0)  # Cap at 1.0 for 10+ newlines
        base_score += structure_bonus
        metrics["structure_bonus"] = round(structure_bonus, 2)
    
    # Penalties
    # Garbage penalty (heavy)
    garbage_penalty = 3.0 * garbage_ratio_val
    base_score -= garbage_penalty
    metrics["garbage_penalty"] = round(garbage_penalty, 2)
    
    # Whitespace penalty (if too high)
    if whitespace_ratio_val > 0.45:
        whitespace_penalty = 1.0 * (whitespace_ratio_val - 0.45)
        base_score -= whitespace_penalty
        metrics["whitespace_penalty"] = round(whitespace_penalty, 2)
    
    # Final score
    final_score = base_score
    
    metrics["final_score"] = round(final_score, 2)
    
    return {
        "score": final_score,
        "metrics": metrics,
    }


def is_bad_ocr(
    text: str,
    confidence: float,
    *,
    settings_obj,
    expected_script: str
) -> Tuple[bool, Dict]:
    """
    Phase 5: Detect if OCR output is "bad" and should trigger re-OCR retry.
    
    Args:
        text: OCR extracted text
        confidence: OCR confidence score (0.0-1.0)
        settings_obj: Settings object with re-OCR thresholds
        expected_script: "urdu"|"english"|"mixed"|"unknown"
    
    Returns:
        Tuple of (is_bad, details_dict)
    """
    details: Dict = {
        "checks": {},
        "reasons": [],
    }
    
    if not text:
        details["checks"]["empty"] = True
        details["reasons"].append("empty_text")
        return True, details
    
    # Calculate metrics
    text_len = len(text)
    garbage_ratio_val = garbage_ratio(text)
    whitespace_ratio_val = whitespace_ratio(text)
    urdu_ratio_val = urdu_char_ratio(text)
    latin_ratio_val = latin_ratio(text)
    
    details["checks"] = {
        "text_len": text_len,
        "confidence": confidence,
        "garbage_ratio": garbage_ratio_val,
        "whitespace_ratio": whitespace_ratio_val,
        "urdu_ratio": urdu_ratio_val,
        "latin_ratio": latin_ratio_val,
    }
    
    is_bad = False
    
    # Condition 1: Confidence too low
    if confidence < settings_obj.OCR_REOCR_MIN_CONFIDENCE:
        is_bad = True
        details["reasons"].append(f"low_confidence:{confidence:.3f}<{settings_obj.OCR_REOCR_MIN_CONFIDENCE}")
    
    # Condition 2: Text too short
    if text_len < settings_obj.OCR_REOCR_MIN_TEXTLEN:
        is_bad = True
        details["reasons"].append(f"too_short:{text_len}<{settings_obj.OCR_REOCR_MIN_TEXTLEN}")
    
    # Condition 3: Garbage ratio too high
    if garbage_ratio_val > settings_obj.OCR_REOCR_MAX_GARBAGE_RATIO:
        is_bad = True
        details["reasons"].append(f"high_garbage:{garbage_ratio_val:.3f}>{settings_obj.OCR_REOCR_MAX_GARBAGE_RATIO}")
    
    # Condition 4: Expected script but nothing readable
    if expected_script in ["urdu", "mixed"]:
        if urdu_ratio_val < 0.05 and latin_ratio_val < 0.05:
            is_bad = True
            details["reasons"].append(f"no_readable_script:urdu={urdu_ratio_val:.3f} latin={latin_ratio_val:.3f}")
    
    details["is_bad"] = is_bad
    
    return is_bad, details


def score_pdf_text_layer(text:
    str, settings_obj) -> Dict[str, Any]:
    """
    Phase 8: Score native PDF text layer quality and determine if acceptable.
    
    Args:
        text: Extracted PDF text
        settings_obj: Settings object with PDF text layer thresholds
    
    Returns:
        Dict with len, ratios, ok boolean, and reason
    """
    text_len = len(text) if text else 0
    
    # Calculate ratios using existing helpers
    urdu_ratio_val = urdu_char_ratio(text)
    latin_ratio_val = latin_ratio(text)
    garbage_ratio_val = garbage_ratio(text)
    whitespace_ratio_val = whitespace_ratio(text)
    
    # Determine if acceptable
    ok = True
    reason = ""
    
    # Check 1: Minimum length
    if text_len < settings_obj.OCR_PDF_TEXT_MIN_LEN:
        ok = False
        reason = f"too_short:{text_len}<{settings_obj.OCR_PDF_TEXT_MIN_LEN}"
    
    # Check 2: Maximum garbage ratio
    if garbage_ratio_val > settings_obj.OCR_PDF_TEXT_MAX_GARBAGE_RATIO:
        ok = False
        reason = f"too_garbage:{garbage_ratio_val:.3f}>{settings_obj.OCR_PDF_TEXT_MAX_GARBAGE_RATIO}"
    
    # Check 3: Minimum script ratio (urdu or latin)
    max_script_ratio = max(urdu_ratio_val, latin_ratio_val)
    if max_script_ratio < settings_obj.OCR_PDF_TEXT_MIN_SCRIPT_RATIO:
        ok = False
        reason = f"no_script:max={max_script_ratio:.3f}<{settings_obj.OCR_PDF_TEXT_MIN_SCRIPT_RATIO}"
    
    if ok:
        reason = "acceptable"
    
    return {
        "len": text_len,
        "urdu_ratio": urdu_ratio_val,
        "latin_ratio": latin_ratio_val,
        "garbage_ratio": garbage_ratio_val,
        "whitespace_ratio": whitespace_ratio_val,
        "ok": ok,
        "reason": reason,
    }

