"""
P16: Candidate gate for validation and normalization before persisting extraction candidates.

This module provides a single entry point normalize_and_validate_candidate() that applies
field-specific validation and normalization rules. This gate is applied before writing
candidates to ocr_extraction_candidates to reduce noise and ensure consistency.
"""
import re
import logging
from typing import Tuple, Optional
from datetime import datetime

from app.services.ocr_text_quality import is_text_corrupted, detect_mojibake

logger = logging.getLogger(__name__)


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in string."""
    return re.sub(r'\s+', ' ', s).strip()


def normalize_and_validate_candidate(field_key: str, value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and normalize a candidate value for a given field_key.
    
    Args:
        field_key: The field key (e.g., "party.cnic", "property.plot_number")
        value: The raw candidate value to validate/normalize
        
    Returns:
        Tuple of (ok: bool, normalized: str | None, reason: str | None)
        - ok: True if value is valid and should be persisted
        - normalized: Normalized value (if ok=True) or None
        - reason: Rejection reason (if ok=False) or None
    """
    if not value:
        return False, None, "empty_value"
    
    # P23: Normalize party role fields (defense in depth - normalize newlines/whitespace)
    if field_key in ("party.seller.names", "party.buyer.names", "party.witness.names"):
        v = value or ""
        v = v.replace("\r", " ").replace("\n", " ")
        v = re.sub(r"[ \t\f\v]+", " ", v).strip()
        if not v:
            return False, None, "empty_after_strip"
        value = v
    
    value = normalize_whitespace(value)
    
    # General checks: mojibake/corruption (apply to all fields)
    is_corrupted, corruption_reason = is_text_corrupted(value, expected_urdu=False)
    if is_corrupted:
        return False, None, f"corrupted_mojibake: {corruption_reason}"
    
    is_mojibake, mojibake_ratio, mojibake_count, total_chars = detect_mojibake(value)
    if is_mojibake or mojibake_ratio > 0.01:
        return False, None, f"corrupted_mojibake: ratio={mojibake_ratio:.3f} count={mojibake_count}/{total_chars}"
    
    # General check: sentence punctuation (indicates narrative)
    if ';' in value:
        return False, None, "contains_semicolon_narrative"
    if value.count('.') > 2 or value.count(':') > 1:
        return False, None, "contains_too_many_punctuation_marks"
    
    # Field-specific validation and normalization
    if field_key == "party.cnic":
        return _validate_cnic(value)
    elif field_key == "property.plot_number":
        return _validate_plot_number(value)
    elif field_key == "property.scheme_name":
        return _validate_scheme_name(value)
    elif field_key == "registry.registry_number":
        return _validate_registry_number(value)
    elif field_key == "document.execution_date":
        return _validate_date(value)
    elif field_key == "consideration.amount":
        return _validate_amount(value)
    else:
        # Unknown field: accept as-is (no normalization)
        return True, value, None


def _validate_cnic(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize CNIC (Pakistan)."""
    # Remove common prefixes
    s = re.sub(r'^(cnic|nic|id)\s*[:]?\s*', '', value, flags=re.IGNORECASE)
    s = s.strip()
    
    # Extract all digits
    digits_only = re.sub(r'\D', '', s)
    
    if len(digits_only) != 13:
        return False, None, "invalid_cnic: not_13_digits"
    
    # Normalize to hyphenated format: XXXXX-XXXXXXX-X
    normalized = f"{digits_only[0:5]}-{digits_only[5:12]}-{digits_only[12:13]}"
    return True, normalized, None


def _validate_plot_number(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize plot number."""
    # Strip anchors (English and Urdu)
    plot_anchors_en = ["plot", "plot no", "plot#", "plot number", "no.", "number"]
    plot_anchors_ur = ["پلاٹ", "نمبر"]
    
    s = value
    for anchor in plot_anchors_en:
        s = re.sub(rf'^{re.escape(anchor)}\s*[:.]?\s*', '', s, flags=re.IGNORECASE)
    for anchor in plot_anchors_ur:
        s = re.sub(rf'^{re.escape(anchor)}\s*[:.]?\s*', '', s)
    s = s.strip()
    
    # Check token count
    tokens = s.split()
    if len(tokens) > 3:
        return False, None, "plot_too_many_tokens"
    
    # Check length
    if len(s) > 12:
        return False, None, "plot_too_long"
    
    # Check for sentence punctuation
    if any(p in s for p in ['.', ';', ':']):
        return False, None, "plot_contains_sentence_punctuation"
    
    # Extract alphanumeric pattern (e.g., "14", "14-A", "14A", "Com-14")
    match = re.match(r'^([A-Za-z]*-?)?(\d+)(-[A-Za-z\d]+)?([A-Za-z]+)?$', s)
    if match:
        # Build normalized: base number + optional suffix
        base_num = match.group(2)
        suffix_parts = []
        if match.group(1):
            suffix_parts.append(match.group(1).rstrip('-'))
        if match.group(3):
            suffix_parts.append(match.group(3).lstrip('-'))
        if match.group(4):
            suffix_parts.append(match.group(4))
        
        if suffix_parts:
            normalized = f"{base_num}-{'-'.join(suffix_parts)}"
        else:
            normalized = base_num
        return True, normalized, None
    
    # Fallback: accept if it looks alphanumeric and reasonable
    if re.match(r'^[\w\-]+$', s) and len(s) <= 12:
        return True, s, None
    
    return False, None, "plot_invalid_format"


def _validate_scheme_name(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize scheme name."""
    s = value.strip()
    
    # Check token count
    tokens = s.split()
    if len(tokens) > 12:
        return False, None, "scheme_too_many_tokens"
    
    # Check for narrative phrases
    narrative_phrases = [
        "in witness", "executed by", "witness whereof", "witnesses named",
        "appears", "vide", "in this regard", "competent", "lawful",
    ]
    s_lower = s.lower()
    for phrase in narrative_phrases:
        if phrase in s_lower:
            return False, None, f"scheme_contains_narrative: {phrase}"
    
    # Check for scheme/housing suffixes (English and Urdu)
    scheme_suffixes_en = ["housing scheme", "scheme", "society", "town", "colony", "city"]
    scheme_suffixes_ur = ["سوسائٹی", "ہاؤسنگ", "ٹاؤن", "کالونی", "اسکیم"]
    
    has_suffix = False
    s_lower = s.lower()
    for suffix in scheme_suffixes_en:
        if suffix in s_lower:
            has_suffix = True
            break
    for suffix in scheme_suffixes_ur:
        if suffix in s:
            has_suffix = True
            break
    
    if not has_suffix:
        # Check if ends with full stop and has verbs (basic heuristic)
        if s.endswith('.') and any(verb in s_lower for verb in ["is", "are", "has", "have", "was", "were"]):
            return False, None, "scheme_ends_with_stop_and_verbs"
    
    # Normalize: collapse whitespace, keep original casing
    normalized = normalize_whitespace(s)
    return True, normalized, None


def _validate_registry_number(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize registry number."""
    s = value.strip()
    
    # Check token count
    tokens = s.split()
    if len(tokens) > 2:
        return False, None, "registry_too_many_tokens"
    
    # Extract digits
    digits_only = re.sub(r'\D', '', s)
    
    if len(digits_only) < 4 or len(digits_only) > 12:
        return False, None, f"registry_invalid_digit_count: {len(digits_only)}"
    
    # Check for long narrative (heuristic: if has many non-digit chars)
    non_digit_chars = len(re.sub(r'\d', '', s))
    if non_digit_chars > len(digits_only):
        return False, None, "registry_contains_too_much_narrative"
    
    # Normalize: keep format but ensure reasonable structure
    # Accept formats like: 1234/2020, 1234-2020, 1234
    normalized = s
    return True, normalized, None


def _validate_date(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize date to ISO format (yyyy-mm-dd)."""
    s = value.strip()
    
    # Try common numeric formats first
    # dd/mm/yyyy or dd-mm-yyyy
    match1 = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', s)
    if match1:
        day, month, year = int(match1.group(1)), int(match1.group(2)), int(match1.group(3))
        if _is_valid_date_parts(day, month, year):
            normalized = f"{year:04d}-{month:02d}-{day:02d}"
            return True, normalized, None
    
    # yyyy-mm-dd
    match2 = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s)
    if match2:
        year, month, day = int(match2.group(1)), int(match2.group(2)), int(match2.group(3))
        if _is_valid_date_parts(day, month, year):
            return True, s, None  # Already ISO format
    
    # Try month name formats: "12 January 2022", "January 12, 2022", "12-Jan-2022"
    month_names = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    
    # Pattern: "DD Month YYYY" or "Month DD, YYYY"
    match3 = re.match(r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', s, re.IGNORECASE)
    if match3:
        day, month_name, year = int(match3.group(1)), match3.group(2).lower(), int(match3.group(3))
        month = month_names.get(month_name)
        if month and _is_valid_date_parts(day, month, year):
            normalized = f"{year:04d}-{month:02d}-{day:02d}"
            return True, normalized, None
    
    match4 = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$', s, re.IGNORECASE)
    if match4:
        month_name, day, year = match4.group(1).lower(), int(match4.group(2)), int(match4.group(3))
        month = month_names.get(month_name)
        if month and _is_valid_date_parts(day, month, year):
            normalized = f"{year:04d}-{month:02d}-{day:02d}"
            return True, normalized, None
    
    # Pattern: "DD-MMM-YYYY"
    match5 = re.match(r'^(\d{1,2})-([A-Za-z]+)-(\d{4})$', s, re.IGNORECASE)
    if match5:
        day, month_name, year = int(match5.group(1)), match5.group(2).lower(), int(match5.group(3))
        month = month_names.get(month_name)
        if month and _is_valid_date_parts(day, month, year):
            normalized = f"{year:04d}-{month:02d}-{day:02d}"
            return True, normalized, None
    
    return False, None, "date_invalid_format"


def _is_valid_date_parts(day: int, month: int, year: int) -> bool:
    """Check if date parts are valid (not checking leap years)."""
    if year < 1900 or year > 2100:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False
    
    # Basic month/day validation (not checking leap years)
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if day > days_in_month[month - 1]:
        return False
    
    return True


def _validate_amount(value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize amount."""
    s = value.strip()
    
    # Remove currency anchors
    s = re.sub(r'^(rs|pkr|rupees?|rupee|₨|consideration)\s*[:]?\s*', '', s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Remove commas and extract number
    s_clean = s.replace(',', '').strip()
    
    # Try to extract number (with optional decimal)
    match = re.match(r'^(\d+(?:\.\d+)?)', s_clean)
    if not match:
        return False, None, "amount_no_number_found"
    
    num_str = match.group(1)
    
    # Check if has explicit currency anchor (more lenient threshold)
    has_anchor = any(anchor in value.lower() for anchor in ["rs", "pkr", "rupees", "rupee", "₨", "consideration"])
    
    # Parse as float
    try:
        amount = float(num_str)
        if amount < 1000 and not has_anchor:
            return False, None, "amount_too_small_without_anchor"
    except ValueError:
        return False, None, "amount_invalid_number"
    
    # Normalize: digits only with optional decimal (e.g., "15600000" or "15600000.00")
    if '.' in num_str:
        # Keep decimal if present
        normalized = num_str
    else:
        normalized = num_str
    
    return True, normalized, None

