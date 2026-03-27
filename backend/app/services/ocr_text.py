"""Phase 5: Text normalization and repair for bank-grade OCR output."""
import logging
import re
import unicodedata
from typing import Dict, Tuple, Optional

from app.services.ocr_text_quality import try_repair_mojibake

logger = logging.getLogger(__name__)

# Urdu/Arabic-Indic digit mappings
URDU_DIGIT_MAP = {
    # Arabic-Indic digits (U+0660-U+0669)
    '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4',
    '\u0665': '5', '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9',
    # Extended Arabic-Indic digits (U+06F0-U+06F9)
    '\u06F0': '0', '\u06F1': '1', '\u06F2': '2', '\u06F3': '3', '\u06F4': '4',
    '\u06F5': '5', '\u06F6': '6', '\u06F7': '7', '\u06F8': '8', '\u06F9': '9',
}

# Urdu punctuation normalization
URDU_PUNCTUATION_MAP = {
    'Û”': '.',  # Urdu full stop
    'ØŒ': ',',  # Urdu comma
}


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace: collapse excessive spaces, normalize newlines, strip trailing spaces.
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Normalize newlines: 
    # Normalize newlines: convert CRLF/CR to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')


    text = text.replace('\n', '\n').replace('\n', '\n')
    
    # Collapse multiple spaces to single space (but preserve newlines)
    # Replace 2+ spaces with single space, but keep newlines
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Collapse multiple newlines to max 2 (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip trailing spaces from each line
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)
    
    # Strip leading/trailing whitespace from entire text
    text = text.strip()
    
    return text


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode using NFKC (Normalization Form Compatibility Composition).
    
    Args:
        text: Text to normalize
    
    Returns:
        NFKC normalized text
    """
    if not text:
        return ""
    
    try:
        return unicodedata.normalize("NFKC", text)
    except Exception as e:
        logger.warning(f"Unicode normalization failed: {e}, using original")
        return text


def fix_mojibake(text:
    str) -> Tuple[str, Optional[str]]:
    """
    Fix mojibake using existing repair logic.
    
    Args:
        text: Text to repair
    
    Returns:
        Tuple of (repaired_text, method_name_or_none)
    """
    if not text:
        return text, None
    
    repaired, method = try_repair_mojibake(text)
    if repaired:
        return repaired, method
    return text, None


def normalize_digits(text:
    str) -> str:
    """
    Normalize Urdu/Arabic-Indic digits to ASCII (0-9).
    
    Also normalizes common Urdu punctuation separators.
    
    Args:
        text: Text to normalize
    
    Returns:
        Text with normalized digits and punctuation
    """
    if not text:
        return ""
    
    result = []
    for char in text:
        # Map Urdu digits to ASCII
        if char in URDU_DIGIT_MAP:
            result.append(URDU_DIGIT_MAP[char])
        # Map Urdu punctuation
        elif char in URDU_PUNCTUATION_MAP:
            result.append(URDU_PUNCTUATION_MAP[char])
        else:
            result.append(char)
    
    return ''.join(result)


def cap_length(text:
    str, max_len: int) -> Tuple[str, bool]:
    """
    Cap text length to maximum.
    
    Args:
        text: Text to cap
        max_len: Maximum length
    
    Returns:
        Tuple of (capped_text, was_truncated)
    """
    if not text:
        return text, False
    
    if len(text) <= max_len:
        return text, False
    
    # Truncate and add indicator
    truncated = text[:max_len]
    return truncated, True


def repair_text(
    text: str,
    *,
    enable_mojibake: bool = True,
    enable_digits: bool = True,
    max_len: int = 200000
) -> Tuple[str, Dict]:
    """
    Phase 5: Repair and normalize OCR text for bank-grade quality.
    
    Pipeline:
    1. Fix mojibake (if enabled)
    2. Unicode normalization (NFKC)
    3. Whitespace normalization
    4. Digit normalization (if enabled)
    5. Length capping
    
    Args:
        text: Raw OCR text
        enable_mojibake: Enable mojibake repair
        enable_digits: Enable digit normalization
        max_len: Maximum text length (safety cap)
    
    Returns:
        Tuple of (repaired_text, metadata_dict)
        Metadata includes: raw_len, actions, truncated, digit_norm, error (if any)
    """
    meta: Dict = {
        "raw_len": len(text) if text else 0,
        "actions": [],
        "truncated": False,
        "digit_norm": False,
    }
    
    if not text:
        return text, meta
    
    original_text = text
    
    try:
        # Step 1: Fix mojibake (if enabled)
        if enable_mojibake:
            text, mojibake_method = fix_mojibake(text)
            if mojibake_method:
                meta["actions"].append(f"mojibake_fix:{mojibake_method}")
        
        # Step 2: Unicode normalization (NFKC)
        text = normalize_unicode(text)
        meta["actions"].append("unicode_nfkc")
        
        # Step 3: Whitespace normalization
        text = normalize_whitespace(text)
        meta["actions"].append("whitespace_norm")
        
        # Step 4: Digit normalization (if enabled)
        if enable_digits:
            text = normalize_digits(text)
            meta["digit_norm"] = True
            meta["actions"].append("digit_norm")
        
        # Step 5: Length capping
        text, was_truncated = cap_length(text, max_len)
        meta["truncated"] = was_truncated
        if was_truncated:
            meta["actions"].append(f"truncated_to_{max_len}")
        
        meta["final_len"] = len(text)
        
        return text, meta
        
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"Text repair failed: {e}")
        meta["error"] = error_msg
        meta["actions"].append(f"error:{error_msg}")
        # Return original text on error
        return original_text, meta

