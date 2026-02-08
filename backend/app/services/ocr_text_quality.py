"""OCR text quality detection and fallback utilities."""
import logging
import re
import unicodedata
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def is_arabic_char(char: str) -> bool:
    """Check if character is in Arabic/Urdu Unicode ranges."""
    code_point = ord(char)
    arabic_unicode_ranges = [
        (0x0600, 0x06FF),  # Arabic block
        (0x0750, 0x077F),  # Arabic Supplement
        (0x08A0, 0x08FF),  # Arabic Extended-A
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ]
    return any(start <= code_point <= end for start, end in arabic_unicode_ranges)


def detect_mojibake(text: str) -> Tuple[bool, float, int, int]:
    """
    Detect mojibake (corrupted encoding) in text.
    
    Args:
        text: Text to check
        
    Returns:
        Tuple of (is_corrupted, mojibake_ratio, mojibake_char_count, total_chars)
    """
    if not text:
        return False, 0.0, 0, 0
    
    # Check for box-drawing characters (common mojibake indicators)
    # Unicode ranges for box-drawing: U+2500-U+257F
    box_drawing_pattern = r'[\u2500-\u257F]'
    box_drawing_matches = len(re.findall(box_drawing_pattern, text))
    
    # Check for block elements (U+2580-U+259F) and geometric shapes (U+25A0-U+25FF)
    block_elements_pattern = r'[\u2580-\u259F]'
    block_elements_matches = len(re.findall(block_elements_pattern, text))
    
    geometric_shapes_pattern = r'[\u25A0-\u25FF]'
    geometric_shapes_matches = len(re.findall(geometric_shapes_pattern, text))
    
    # Check for specific mojibake characters we've seen (expanded list)
    # Includes: "┌⌐╪º╪┤┘ü ╪▓╪º╪¿╪»" and other common corruption chars
    specific_mojibake_chars = [
        '╪', '┘', '┌', '▒', '█', '▓', '⌐', 'º', '┤', 'ü', '¿', '»',  # From user's example
        '║', '╔', '╗', '╚', '╝', '═', '╬', '╩', '╦', '╠', '╣', '╤', '╧', '╥', '╨', 
        '╙', '╘', '╒', '╓', '╕', '╖', '╛', '╜', '╞', '╟', '╡', '╢', '╫', '╭', '╮', 
        '╯', '╰', '╱', '╲', '╳', '╴', '╵', '╶', '╷', '╸', '╹', '╺', '╻', '╼', '╽', '╾', '╿',
        '┐', '└', '├', '┬', '┴', '┼', '░',  # Additional box drawing
        'ΓÇ', 'â€',  # UTF-8 mojibake sequences (will be caught as multi-char)
    ]
    specific_mojibake_count = sum(1 for c in text if c in specific_mojibake_chars)
    
    # Check for common UTF-8 mojibake byte sequences (when incorrectly decoded)
    # These appear as sequences like "â€" when UTF-8 is decoded as Latin-1
    mojibake_patterns = [
        r'â€[™"]',  # Common UTF-8 mojibake
        r'â€™',  # Apostrophe mojibake
        r'â€œ',  # Quote mojibake
        r'â€"',  # Dash mojibake
        r'â€"',  # Another dash variant
    ]
    pattern_matches = sum(len(re.findall(pattern, text)) for pattern in mojibake_patterns)
    
    # Check for control characters and unusual symbols that indicate corruption
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    
    total_mojibake = box_drawing_matches + block_elements_matches + geometric_shapes_matches + specific_mojibake_count + pattern_matches + control_chars
    total_chars = len(text)
    
    if total_chars == 0:
        return False, 0.0, 0, 0
    
    mojibake_ratio = total_mojibake / total_chars
    
    # Threshold 1: if > 2% of characters are mojibake, consider corrupted
    # Threshold 2: if > 2 occurrences of mojibake chars (high density for short strings)
    is_corrupted = mojibake_ratio > 0.02 or total_mojibake > 2
    
    return is_corrupted, mojibake_ratio, total_mojibake, total_chars


def detect_expected_urdu_but_missing(text: str) -> bool:
    """
    Detect if text should contain Urdu but doesn't (indicates corruption).
    
    Heuristics:
    - If text contains CNIC patterns (13 digits) but no Arabic/Urdu letters
    - If text contains common Urdu keywords in English but no Arabic script
    """
    if not text:
        return False
    
    # Check for CNIC pattern (13 digits, possibly with hyphens/spaces)
    cnic_pattern = r'\b\d{5}[- ]?\d{7}[- ]?\d{1}\b'
    has_cnic = bool(re.search(cnic_pattern, text))
    
    # Check for Arabic/Urdu letters
    has_arabic = any(is_arabic_char(c) for c in text)
    
    # Check for common Urdu keywords in English (indicating this should be Urdu)
    urdu_keywords_english = [
        "bai", "mushteri", "gawah", "nam", "walediat", "shanaakhti",
        "card", "number", "cnic", "nic"
    ]
    has_urdu_keywords = any(keyword.lower() in text.lower() for keyword in urdu_keywords_english)
    
    # If we have CNIC or Urdu keywords but no Arabic script, likely corrupted
    if (has_cnic or has_urdu_keywords) and not has_arabic:
        # Additional check: if text has high mojibake ratio, definitely corrupted
        is_corrupted, mojibake_ratio, _, _ = detect_mojibake(text)
        if is_corrupted or mojibake_ratio > 0.01:
            return True
    
    return False


def looks_like_arabic_script(text: str) -> bool:
    """
    Check if text looks like Arabic script (Urdu/Arabic).
    Returns True if Arabic-script letter ratio > 0.20.
    """
    if not text:
        return False
    
    # Remove whitespace for ratio calculation
    non_whitespace = ''.join(c for c in text if not c.isspace())
    if not non_whitespace:
        return False
    
    # Count Arabic letters
    arabic_count = sum(1 for c in non_whitespace if is_arabic_char(c))
    
    # Ratio threshold: >20% Arabic letters
    arabic_ratio = arabic_count / len(non_whitespace)
    return arabic_ratio > 0.20


def is_text_corrupted(text: str, expected_urdu: bool = False) -> Tuple[bool, str]:
    """
    Check if text is corrupted (mojibake or expected Urdu missing).
    
    Args:
        text: Text to check
        expected_urdu: If True, also check if Arabic script is expected but missing
        
    Returns:
        Tuple of (is_corrupted, reason)
    """
    if not text:
        return False, "empty"
    
    # Check for mojibake
    is_corrupted_mojibake, mojibake_ratio, mojibake_count, total_chars = detect_mojibake(text)
    if is_corrupted_mojibake:
        return True, f"mojibake_ratio={mojibake_ratio:.3f} mojibake_chars={mojibake_count}/{total_chars}"
    
    # Check for expected Urdu but missing
    if detect_expected_urdu_but_missing(text):
        return True, "expected_urdu_but_missing"
    
    # If expected_urdu is True, check if Arabic script is present
    if expected_urdu and not looks_like_arabic_script(text):
        return True, "expected_urdu_but_no_arabic_script"
    
    return False, "ok"


def try_repair_mojibake(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempt to repair mojibake using encoding fixes.
    
    This tries common encoding mismatches (latin1->utf8, cp1252->utf8) to fix
    corrupted text. Validates repair: mojibake must be gone, and result should
    be more Arabic-like than input (or at least not corrupted).
    
    Args:
        text: Text to repair
        
    Returns:
        Tuple of (repaired_text, method_name) or (None, None) if not repairable
    """
    if not text:
        return None, None
    
    # Check if mojibake exists
    is_mojibake, mojibake_ratio, _, _ = detect_mojibake(text)
    if not is_mojibake:
        return None, None
    
    # Calculate Arabic ratio before repair (for comparison)
    arabic_ratio_before = sum(1 for c in text if is_arabic_char(c)) / len(text) if text else 0.0
    
    # Try latin1 -> utf-8 (common for Urdu OCR corruption)
    try:
        candidate = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        if candidate and len(candidate) >= 3:
            # Validate repair: check mojibake is gone
            is_mojibake_after, mojibake_ratio_after, _, _ = detect_mojibake(candidate)
            if not is_mojibake_after:
                # Check if result is more Arabic-like than input (or at least not corrupted)
                arabic_ratio_after = sum(1 for c in candidate if is_arabic_char(c)) / len(candidate) if candidate else 0.0
                if looks_like_arabic_script(candidate) or arabic_ratio_after > arabic_ratio_before:
                    logger.info(
                        f"OCR_REPAIR: method=latin1_to_utf8 mojibake_before={mojibake_ratio:.3f} "
                        f"mojibake_after={mojibake_ratio_after:.3f} len_before={len(text)} len_after={len(candidate)}"
                    )
                    return candidate, "latin1_to_utf8"
    except Exception as e:
        logger.debug(f"OCR_REPAIR: latin1_to_utf8 failed: {e}")
    
    # Try cp1252 -> utf-8
    try:
        candidate = text.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
        if candidate and len(candidate) >= 3:
            # Validate repair: check mojibake is gone
            is_mojibake_after, mojibake_ratio_after, _, _ = detect_mojibake(candidate)
            if not is_mojibake_after:
                # Check if result is more Arabic-like than input (or at least not corrupted)
                arabic_ratio_after = sum(1 for c in candidate if is_arabic_char(c)) / len(candidate) if candidate else 0.0
                if looks_like_arabic_script(candidate) or arabic_ratio_after > arabic_ratio_before:
                    logger.info(
                        f"OCR_REPAIR: method=cp1252_to_utf8 mojibake_before={mojibake_ratio:.3f} "
                        f"mojibake_after={mojibake_ratio_after:.3f} len_before={len(text)} len_after={len(candidate)}"
                    )
                    return candidate, "cp1252_to_utf8"
    except Exception as e:
        logger.debug(f"OCR_REPAIR: cp1252_to_utf8 failed: {e}")
    
    return None, None


def normalize_text_for_persistence(text: str) -> str:
    """
    P17: Normalize text to UTF-8 safe format before persistence.
    
    Steps:
    1. Strip nulls and control chars (except \n, \r, \t)
    2. Normalize Unicode (NFC normalization)
    3. If still corrupted, attempt repair
    4. Return normalized text (or original if all fails)
    
    This should be called BEFORE storing ocr_text in database.
    
    Args:
        text: Raw OCR text (may contain mojibake or encoding issues)
        
    Returns:
        Normalized UTF-8 safe text
    """
    if not text:
        return ""
    
    # Step 1: Strip nulls and control chars (keep \n, \r, \t)
    text_clean = ''.join(c for c in text if c == '\n' or c == '\r' or c == '\t' or (ord(c) >= 32 and ord(c) != 127))
    
    # Step 2: Normalize Unicode (NFC normalization)
    try:
        text_normalized = unicodedata.normalize("NFC", text_clean)
    except Exception as e:
        logger.warning(f"OCR_NORMALIZE: Unicode normalization failed, using cleaned text: {e}")
        text_normalized = text_clean
    
    # Step 3: Check if still corrupted and attempt repair
    is_corrupted, reason = is_text_corrupted(text_normalized)
    if is_corrupted:
        logger.info(f"OCR_NORMALIZE: text still corrupted after normalization, attempting repair: {reason}")
        repaired_text, repair_method = try_repair_mojibake(text_normalized)
        if repaired_text and not is_text_corrupted(repaired_text)[0]:
            logger.info(f"OCR_NORMALIZE: repair succeeded via {repair_method}, using repaired text")
            return repaired_text
        else:
            logger.warning(f"OCR_NORMALIZE: repair failed, returning normalized text (may still be corrupted)")
    
    return text_normalized
