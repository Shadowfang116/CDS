"""Phase 7: Urdu legal/property domain normalization for bank-grade OCR."""
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set

from app.services.ocr_text import normalize_whitespace

logger = logging.getLogger(__name__)

# Urdu month names
URDU_MONTHS = {
    "Ø¬Ù†ÙˆØ±ÛŒ": 1, "ÙØ±ÙˆØ±ÛŒ": 2, "Ù…Ø§Ø±Ú†": 3, "Ø§Ù¾Ø±ÛŒÙ„": 4,
    "Ù…Ø¦ÛŒ": 5, "Ø¬ÙˆÙ†": 6, "Ø¬ÙˆÙ„Ø§Ø¦ÛŒ": 7, "Ø§Ú¯Ø³Øª": 8,
    "Ø³ØªÙ…Ø¨Ø±": 9, "Ø§Ú©ØªÙˆØ¨Ø±": 10, "Ù†ÙˆÙ…Ø¨Ø±": 11, "Ø¯Ø³Ù…Ø¨Ø±": 12,
}

# English month names (abbreviated and full)
ENGLISH_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def normalize_separators(text: str) -> str:
    """
    Normalize Urdu punctuation variants to ASCII equivalents in a copy.
    
    Args:
        text: Text to normalize
    
    Returns:
        Copy with normalized separators
    """
    if not text:
        return ""
    
    # Urdu full stop and comma normalization
    text = text.replace('Û”', '.').replace('ØŒ', ',')
    
    return text


def strip_zero_width(text: str) -> str:
    """
    Remove zero-width characters: \u200b \u200c \u200d \ufeff
    
    Args:
        text: Text to clean
    
    Returns:
        Text without zero-width characters
    """
    if not text:
        return ""
    
    # Remove zero-width space, zero-width non-joiner, zero-width joiner, BOM
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    
    return text


def normalize_cnic(text: str, strict: bool = True) -> List[Dict[str, any]]:
    """
    Detect and normalize CNIC (Computerized National Identity Card) numbers.
    
    Formats:
    - 13 digits continuous: 3520112345671
    - 5-7-1 format: 35201-1234567-1
    - With Urdu digits (already normalized in Phase 5)
    
    Args:
        text: Text to search
        strict: Only match high-confidence patterns
    
    Returns:
        List of CNIC hints
    """
    hints = []
    seen = set()  # Deduplicate by normalized value
    
    # Pattern 1: 5-7-1 format (#####-#######-#)
    pattern1 = r'\b(\d{5})-(\d{7})-(\d{1})\b'
    for match in re.finditer(pattern1, text):
        cnic = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        if cnic not in seen:
            seen.add(cnic)
            line_num = text[:match.start()].count('\n')
            hints.append({
                "type": "cnic",
                "value": cnic,
                "raw": match.group(0),
                "line": line_num,
                "confidence": "high",
            })
    
    # Pattern 2: 13 digits continuous (if strict=False or if context suggests CNIC)
    pattern2 = r'\b(\d{13})\b'
    for match in re.finditer(pattern2, text):
        digits = match.group(1)
        # Check if it's not part of a longer number

        start, end = match.start(), match.end()

        if (start == 0 or not text[start-1].isdigit()) and (end >= len(text) or not text[end].isdigit()):

            # Format as 5-7-1

            cnic = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"

            if cnic not in seen:

                seen.add(cnic)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "cnic",

                    "value": cnic,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high" if strict else "med",

                })

    

    return hints





def normalize_dates(text: str, strict: bool = True, tz: str = "Asia/Karachi") -> List[Dict[str, any]]:

    """

    Detect and normalize dates in multiple formats.

    

    Formats:

    - dd.mm.yyyy, dd-mm-yyyy, dd/mm/yyyy

    - yyyy-mm-dd

    - Urdu textual months: Ø¬Ù†ÙˆØ±ÛŒØŒ ÙØ±ÙˆØ±ÛŒØŒ etc.

    - English months: Jan, January, etc.

    

    Args:

        text: Text to search

        strict: Only normalize unambiguous dates

        tz: Timezone (for context, not used in Phase 7)

    

    Returns:

        List of date hints

    """

    hints = []

    seen = set()

    

    # Pattern 1: ISO format yyyy-mm-dd

    pattern_iso = r'\b(\d{4})-(\d{2})-(\d{2})\b'

    for match in re.finditer(pattern_iso, text):

        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))

        if 1 <= month <= 12 and 1 <= day <= 31:

            date_str = f"{year:04d}-{month:02d}-{day:02d}"

            if date_str not in seen:

                seen.add(date_str)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "date",

                    "value": date_str,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Pattern 2: dd.mm.yyyy, dd-mm-yyyy, dd/mm/yyyy

    pattern_dmy = r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b'

    for match in re.finditer(pattern_dmy, text):

        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))

        

        # Check ambiguity: if d > 12, it's definitely day; if m > 12, it's definitely month

        # In strict mode, only normalize if unambiguous

        if strict:

            if d > 12:  # Definitely day

                if 1 <= m <= 12 and 1 <= d <= 31:

                    date_str = f"{y:04d}-{m:02d}-{d:02d}"

                    if date_str not in seen:

                        seen.add(date_str)

                        line_num = text[:match.start()].count('\n')

                        hints.append({

                            "type": "date",

                            "value": date_str,

                            "raw": match.group(0),

                            "line": line_num,

                            "confidence": "high",

                        })

            elif m > 12:  # Definitely month

                if 1 <= d <= 31:

                    date_str = f"{y:04d}-{m:02d}-{d:02d}"

                    if date_str not in seen:

                        seen.add(date_str)

                        line_num = text[:match.start()].count('\n')

                        hints.append({

                            "type": "date",

                            "value": date_str,

                            "raw": match.group(0),

                            "line": line_num,

                            "confidence": "high",

                        })

            else:

                # Ambiguous: emit hint with raw value only

                raw_val = match.group(0)

                if raw_val not in seen:

                    seen.add(raw_val)

                    line_num = text[:match.start()].count('\n')

                    hints.append({

                        "type": "date",

                        "value": None,  # Cannot normalize unambiguously

                        "raw": raw_val,

                        "line": line_num,

                        "confidence": "low",

                    })

        else:

            # Non-strict: assume dd.mm.yyyy

            if 1 <= m <= 12 and 1 <= d <= 31:

                date_str = f"{y:04d}-{m:02d}-{d:02d}"

                if date_str not in seen:

                    seen.add(date_str)

                    line_num = text[:match.start()].count('\n')

                    hints.append({

                        "type": "date",

                        "value": date_str,

                        "raw": match.group(0),

                        "line": line_num,

                        "confidence": "med",

                    })

    

    # Pattern 3: Urdu textual months

    # Match: "30 Ø¬Ù†ÙˆØ±ÛŒ 2024" or "30-Ø¬Ù†ÙˆØ±ÛŒ-2024" etc.

    urdu_month_pattern = r'\b(\d{1,2})\s*[-.]?\s*(' + '|'.join(re.escape(m) for m in URDU_MONTHS.keys()) + r')\s*[-.]?\s*(\d{4})\b'

    for match in re.finditer(urdu_month_pattern, text, re.IGNORECASE):

        day = int(match.group(1))

        month_name = match.group(2)

        year = int(match.group(3))

        

        month_num = URDU_MONTHS.get(month_name)

        if month_num and 1 <= day <= 31:

            date_str = f"{year:04d}-{month_num:02d}-{day:02d}"

            if date_str not in seen:

                seen.add(date_str)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "date",

                    "value": date_str,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Pattern 4: English textual months

    # Match: "30 Jan 2024" or "30-January-2024" etc.

    eng_month_pattern = r'\b(\d{1,2})\s*[-.]?\s*(' + '|'.join(ENGLISH_MONTHS.keys()) + r')\s*[-.]?\s*(\d{4})\b'

    for match in re.finditer(eng_month_pattern, text, re.IGNORECASE):

        day = int(match.group(1))

        month_name = match.group(2).lower()

        year = int(match.group(3))

        

        month_num = ENGLISH_MONTHS.get(month_name)

        if month_num and 1 <= day <= 31:

            date_str = f"{year:04d}-{month_num:02d}-{day:02d}"

            if date_str not in seen:

                seen.add(date_str)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "date",

                    "value": date_str,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    return hints





def normalize_property_refs(text: str, strict: bool = True) -> List[Dict[str, any]]:

    """

    Detect revenue/property references: Khewat, Khatoni, Khasra, Mutation.

    

    Args:

        text: Text to search

        strict: Only match high-confidence patterns

    

    Returns:

        List of property reference hints

    """

    hints = []

    seen = set()

    

    # Khewat / Ú©Ú¾Ø§ØªÛ / Ú©Ú¾Ø§ØªÛ Ù†Ù…Ø¨Ø±

    khewat_patterns = [

        r'(?:Ú©Ú¾Ø§ØªÛ|Ú©Ú¾ÛŒÙˆÙ¹|Khewat|Khewat\s+No\.?|Ú©Ú¾Ø§ØªÛ\s+Ù†Ù…Ø¨Ø±)\s*[:\-]?\s*(\d+)',

        r'(\d+)\s*(?:Ú©Ú¾Ø§ØªÛ|Ú©Ú¾ÛŒÙˆÙ¹|Khewat)',

    ]

    for pattern in khewat_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            value = match.group(1)

            key = f"khewat:{value}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "khewat",

                    "value": value,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Khatoni / Ú©Ú¾ØªÙˆÙ†ÛŒ / khatuni / Khatoni No

    khatoni_patterns = [

        r'(?:Ú©Ú¾ØªÙˆÙ†ÛŒ|Khatoni|Khatoni\s+No\.?|Ú©Ú¾ØªÙˆÙ†ÛŒ\s+Ù†Ù…Ø¨Ø±)\s*[:\-]?\s*(\d+)',

    ]

    for pattern in khatoni_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            value = match.group(1)

            key = f"khatoni:{value}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "khatoni",

                    "value": value,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Khatoni range: "1180 ØªØ§ 1190" or "1180 to 1190"

    khatoni_range_patterns = [

        r'(\d+)\s*(?:ØªØ§|to|-)\s*(\d+)\s*(?:Ú©Ú¾ØªÙˆÙ†ÛŒ|Khatoni)',

    ]

    for pattern in khatoni_range_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            value = f"{match.group(1)}-{match.group(2)}"

            key = f"khatoni_range:{value}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "khatoni_range",

                    "value": value,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Khasra / Ø®Ø³Ø±Û

    khasra_patterns = [

        r'(?:Ø®Ø³Ø±Û|Khasra|Khasra\s+No\.?)\s*[:\-]?\s*([\d/]+)',

        r'([\d/]+)\s*(?:Ø®Ø³Ø±Û|Khasra)',

    ]

    for pattern in khasra_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            value = match.group(1)

            key = f"khasra:{value}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "khasra",

                    "value": value,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    # Mutation / Ø§Ù†ØªÙ‚Ø§Ù„ / Intiqal / Mutation No

    mutation_patterns = [

        r'(?:Ø§Ù†ØªÙ‚Ø§Ù„|Mutation|Mutation\s+No\.?|Intiqal)\s*[:\-]?\s*(\d+)',

        r'(\d+)\s*(?:Ø§Ù†ØªÙ‚Ø§Ù„|Mutation|Intiqal)',

    ]

    for pattern in mutation_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            value = match.group(1)

            key = f"mutation:{value}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "mutation",

                    "value": value,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "high",

                })

    

    return hints





def normalize_area_units(text: str, strict: bool = True) -> List[Dict[str, any]]:

    """

    Detect and normalize area/unit references (kanal, marla, sqft).

    

    Formats:

    - "4 kanal 2 marla" or "4 Ú©Ù†Ø§Ù„ 2 Ù…Ø±Ù„Û"

    - "500 sqft" or "500 Ù…Ø±Ø¨Ø¹ ÙÙ¹"

    

    Args:

        text: Text to search

        strict: Only match high-confidence patterns

    

    Returns:

        List of area hints

    """

    hints = []

    seen = set()

    

    # Pattern: "X kanal Y marla" or "X Ú©Ù†Ø§Ù„ Y Ù…Ø±Ù„Û"

    kanal_marla_patterns = [

        r'(\d+)\s*(?:Ú©Ù†Ø§Ù„|kanal)\s+(\d+)\s*(?:Ù…Ø±Ù„Û|marla)',

        r'(\d+)\s*(?:kanal|Ú©Ù†Ø§Ù„)\s+(\d+)\s*(?:marla|Ù…Ø±Ù„Û)',

    ]

    for pattern in kanal_marla_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            kanal = int(match.group(1))

            marla = int(match.group(2))

            key = f"area:{kanal}:{marla}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "area",

                    "unit": "kanal-marla",

                    "kanal": kanal,

                    "marla": marla,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "med",

                })

    

    # Pattern: "X sqft" or "X Ù…Ø±Ø¨Ø¹ ÙÙ¹" or "X sq. ft."

    sqft_patterns = [

        r'(\d+)\s*(?:Ù…Ø±Ø¨Ø¹\s*ÙÙ¹|sq\.?\s*ft\.?|sqft)',

    ]

    for pattern in sqft_patterns:

        for match in re.finditer(pattern, text, re.IGNORECASE):

            sqft = int(match.group(1))

            key = f"area_sqft:{sqft}"

            if key not in seen:

                seen.add(key)

                line_num = text[:match.start()].count('\n')

                hints.append({

                    "type": "area",

                    "unit": "sqft",

                    "sqft": sqft,

                    "raw": match.group(0),

                    "line": line_num,

                    "confidence": "med",

                })

    

    return hints





def derive_domain_hints(text: str, *, strict: bool = True, max_hints: int = 100) -> Dict[str, any]:

    """

    Phase 7: Derive domain hints from Urdu legal/property OCR text.

    

    Args:

        text: OCR text (should be repaired/normalized from Phase 5)

        strict: Only apply transforms with strong match

        max_hints: Maximum number of hints to return

    

    Returns:

        Dict with hints, normalized_text (if inplace), actions, stats

    """

    if not text:

        return {

            "hints": [],

            "normalized_text": "",

            "actions": [],

            "stats": {"hints_count": 0},

        }

    

    # Prepare normalized text (copy for inplace mode)

    normalized_text = text

    actions = []

    

    # Step 1: Normalize separators and strip zero-width chars

    normalized_text = normalize_separators(normalized_text)

    normalized_text = strip_zero_width(normalized_text)

    if normalized_text != text:

        actions.append("normalize_separators")

        actions.append("strip_zero_width")

    

    # Step 2: Collect hints from all normalizers

    all_hints = []

    

    # CNIC

    cnic_hints = normalize_cnic(text, strict=strict)

    all_hints.extend(cnic_hints)

    

    # Dates

    date_hints = normalize_dates(text, strict=strict)

    all_hints.extend(date_hints)

    

    # Property references

    prop_hints = normalize_property_refs(text, strict=strict)

    all_hints.extend(prop_hints)

    

    # Area/units

    area_hints = normalize_area_units(text, strict=strict)

    all_hints.extend(area_hints)

    

    # Step 3: Deduplicate by (type, value) and cap

    seen_keys = set()

    unique_hints = []

    for hint in all_hints:

        key = (hint["type"], str(hint.get("value", "")))

        if key not in seen_keys:

            seen_keys.add(key)

            unique_hints.append(hint)

            if len(unique_hints) >= max_hints:

                break

    

    return {

        "hints": unique_hints,

        "normalized_text": normalized_text,

        "actions": actions,

        "stats": {"hints_count": len(unique_hints)},

    }




