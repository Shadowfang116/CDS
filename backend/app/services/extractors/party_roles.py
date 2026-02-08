"""Party role extraction for sale deeds (seller, buyer, witness)."""
import re
import logging
import os
import unicodedata
from typing import List, Dict, Optional, Tuple, Pattern
from dataclasses import dataclass

from app.services.extractors.name_lines import extract_name_lines, normalize_whitespace
from app.services.extractors.validators import is_probably_name_line, is_plausible_party_name

logger = logging.getLogger(__name__)

# Debug flag for party role extraction
PARTY_ROLES_DEBUG = os.getenv("PARTY_ROLES_DEBUG", "false").lower() == "true"


def normalize_party_role_value(s: str) -> str:
    """
    P23: Canonicalize party role values by removing newlines and normalizing whitespace.
    
    Keep Urdu joiners; only normalize whitespace/newlines.
    """
    if not s:
        return ""
    # Replace carriage return and newline with space
    s = s.replace("\r", " ").replace("\n", " ")
    # Collapse all whitespace sequences (space, tab, form feed, vertical tab) to single space
    s = re.sub(r"[ \t\f\v]+", " ", s).strip()
    return s


@dataclass
class PageOCR:
    """OCR text for a single page with document context."""
    document_id: str
    document_name: str
    page_number: int
    text: str


# Sale deed indicators (English and Urdu)
SALE_DEED_KEYWORDS_EN = [
    "sale deed", "deed of sale", "sale agreement", "agreement of sale",
    "vendor", "vendee", "purchaser", "seller", "buyer",
    "consideration", "sold to", "purchased from", "transfer deed"
]

SALE_DEED_KEYWORDS_URDU = [
    "بیع نامہ", "فروخت نامہ", "فروخت کنندہ", "خریدار", "گواہ",
    "بیع", "فروخت", "خریداری", "فروخت کنندگان", "خریداران"
]

# Stopwords for names (English and Urdu)
NAME_STOPWORDS_EN = {
    "mr", "mrs", "miss", "ms", "dr", "prof", "sir", "madam",
    "son", "s/o", "d/o", "w/o", "c/o", "father", "mother",
    "district", "tehsil", "cnic", "address", "plot", "khasra",
    "resident", "of", "the", "and", "or"
}

NAME_STOPWORDS_URDU = {
    "ولد", "ساکن", "ضلع", "تحصیل", "شناختی", "کارڈ", "نمبر",
    "مکان", "پلاٹ", "رہائشی", "کا", "کی", "کے", "اور", "یا"
}

# Common name delimiters
NAME_DELIMITERS = [
    ",", ";", " and ", " & ", "،", "؛", " و ", " اور "
]

# Stop tokens for name cleaning (Urdu + English)
STOP_TOKENS_URDU = [
    "ولد", "ولدہ", "ساکن", "رہائشی", "تحصیل", "ضلع", "شناختی", "کارڈ", "قوم", "پتہ",
    "نمبر", "مکان", "پلاٹ", "کا", "کی", "کے", "اور", "یا", "نام", "ولدیت"
]

STOP_TOKENS_EN = [
    "s/o", "d/o", "w/o", "c/o", "son of", "daughter of", "wife of",
    "resident", "cnic", "nic", "address", "district", "tehsil", "district",
    "executed by", "witness", "vendor", "vendee", "signature", "signed", "sealed"
]

# Leading labels to remove (Urdu + English)
LEADING_LABELS_URDU = [
    "فریق اول", "فریق دوم", "بائع", "مشتری", "خریدار", "گواہ", "گواہان",
    "فروخت کنندہ", "فروشندہ", "شاہد", "شاہدین", "نام", "ولدیت"
]

LEADING_LABELS_EN = [
    "seller", "buyer", "vendor", "purchaser", "vendee", "witness", "witnesses",
    "first party", "second party", "attesting witness", "executed by", "name"
]


def detect_sale_deed(text: str) -> bool:
    """
    Detect if OCR text contains strong sale deed indicators.
    
    Returns True if text contains sale deed keywords (English or Urdu).
    """
    text_normalized = normalize_whitespace(text.lower())
    
    # Check English keywords
    for keyword in SALE_DEED_KEYWORDS_EN:
        if keyword.lower() in text_normalized:
            return True
    
    # Check Urdu keywords (case-insensitive matching not needed for Urdu)
    for keyword in SALE_DEED_KEYWORDS_URDU:
        if keyword in text:
            return True
    
    return False


def name_quality_score(s: str) -> float:
    """
    Score a string for likelihood of being a person name (0.0 to 1.0).
    Higher score = more likely to be a name.
    Returns 0.0 for clearly invalid names.
    
    Strengthened to reject:
    - Known boilerplate tokens (EXECUTED BY, IN WITNESS WHEREOF, etc.)
    - Gibberish (low letter ratio, excessive punctuation, repeated short tokens)
    - Label-only text (نام, ولدیت, etc.)
    """
    if not s or len(s.strip()) < 2:
        return 0.0
    
    s_norm = normalize_line(s)
    s_lower = s_norm.lower()
    
    # Expanded blacklist tokens (case-insensitive)
    blacklist_tokens = [
        "executed by", "in witness", "witness whereof", "vendor", "vendee", "party",
        "schedule of property", "description", "north", "south", "east", "west",
        "signed", "sealed", "delivered", "hereinafter", "called", "deed", "sale",
        "signature", "witness", "attesting", "property", "schedule", "hereby",
        # Urdu label-only tokens
        "نام", "ولدیت", "شناختی کارڈ نمبر", "شناختی", "کارڈ", "نمبر",
        "ساکن", "رہائشی", "ضلع", "تحصیل", "پتہ", "مکان", "پلاٹ"
    ]
    for token in blacklist_tokens:
        if token in s_lower or token in s_norm:
            return 0.0
    
    # Reject if mostly punctuation or single short word
    # Include Arabic Presentation Forms for better Urdu detection
    letter_chars = re.sub(r'[^\w\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', s_norm)
    if len(letter_chars.strip()) < 3:
        return 0.0
    
    # Calculate letter ratio
    total_chars = len(s_norm)
    # Include Arabic Presentation Forms for better Urdu detection
    letter_count = len(re.findall(r'[a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', s_norm))
    letter_ratio = letter_count / total_chars if total_chars > 0 else 0.0
    
    # Calculate Arabic/Urdu ratio
    arabic_count = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', s_norm))
    arabic_ratio = arabic_count / total_chars if total_chars > 0 else 0.0
    
    # Gibberish detector: reject if too many punctuation/symbols or too few letters
    if letter_ratio < 0.3:  # Less than 30% letters
        return 0.0
    
    # Reject obvious OCR gibberish (mixed low letter ratio and low Arabic ratio)
    if letter_ratio < 0.55 and arabic_ratio < 0.20:
        return 0.0
    
    # Reject if contains repeated weird patterns (e.g., "De eo re")
    if re.search(r'\b([a-z]{1,2})\s+\1\s+[a-z]{1,2}\b', s_lower):
        return 0.0
    
    # Reject "De eo re" pattern: all tokens are length <= 3 and token_count >= 3
    tokens = s_norm.split()
    if len(tokens) >= 3:
        all_short = all(len(t) <= 3 for t in tokens)
        if all_short:
            return 0.0
    
    # Reject if too many short tokens (likely OCR fragments)
    short_tokens = [t for t in tokens if len(t) <= 2]
    if len(short_tokens) > len(tokens) * 0.5 and len(tokens) > 2:
        return 0.0
    
    # Reject if contains repeated short tokens pattern (e.g., "De eo re wal Sch Ei")
    if re.search(r'\b([a-z]{1,3})\s+[a-z]{1,3}\s+[a-z]{1,3}\s+[a-z]{1,3}\b', s_lower):
        # Check if all are very short
        matches = re.findall(r'\b([a-z]{1,3})\s+[a-z]{1,3}\s+[a-z]{1,3}\s+[a-z]{1,3}\b', s_lower)
        if matches:
            return 0.0
    
    # Reject if contains too many non-alphanumerics
    # Include Arabic Presentation Forms for better Urdu detection
    punct_count = len(re.findall(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', s_norm))
    punct_ratio = punct_count / total_chars if total_chars > 0 else 0.0
    if punct_ratio > 0.3:
        return 0.0
    
    score = 0.5  # Base score
    
    # Boost for Urdu names
    if arabic_ratio > 0.3:
        score += 0.3
        # Check for Urdu kinship patterns (but not if it's just the label)
        has_kinship = bool(re.search(r'ولد|بن|بنت', s_norm))
        if has_kinship and len(s_norm) > 5:
            # Require non-trivial name segment with kinship
            # Extract name part (before kinship token)
            kinship_match = re.search(r'(.+?)\s*(?:ولد|بن|بنت)', s_norm)
            if kinship_match:
                name_part = kinship_match.group(1).strip()
                if len(name_part) >= 3:  # Non-trivial name segment
                    score += 0.1
        # Require at least 2 Urdu words OR longer mixed strings with org keywords
        # Include Arabic Presentation Forms for better Urdu detection
        urdu_words = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+', s_norm)
        if len(urdu_words) >= 2:
            score += 0.1
            # Explicit check: "کاشف زابد" should pass (2 Urdu words, no kinship needed)
            # This is a valid name pattern
        elif len(s_norm) > 15 and re.search(r'بینک|Bank|Limited|Ltd|Pvt', s_norm, re.IGNORECASE):
            # Allow longer org names
            score += 0.1
        elif not has_kinship and len(urdu_words) < 2:
            # Single Urdu word without kinship - likely incomplete
            # BUT: if it's a reasonable length (4+ chars) and has good letter ratio, allow it
            if len(urdu_words) == 1 and len(urdu_words[0]) >= 4 and letter_ratio > 0.7:
                score += 0.05  # Small boost for single valid Urdu word
            elif len(urdu_words) == 0:
                # No Urdu words at all - reject
                return 0.0
            else:
                # Single short Urdu word - reject
                return 0.0
    
    # Boost for English names (at least 2 alphabetic tokens, at least one length>=4)
    tokens = s_norm.split()
    alphabetic_tokens = [t for t in tokens if re.match(r'^[a-zA-Z]+$', t) and len(t) >= 2]
    if len(alphabetic_tokens) >= 2:
        # Require at least one token length >= 4 (rejects "De eo re")
        has_long_token = any(len(t) >= 4 for t in alphabetic_tokens)
        if has_long_token:
            score += 0.2
            # Penalize if punctuation ratio is high
            if punct_ratio < 0.15:
                score += 0.1
        else:
            # All tokens are short (<=3), likely gibberish
            return 0.0
    
    # Penalize for short length
    if len(s_norm) < 4:
        score -= 0.2
    elif 4 <= len(s_norm) <= 60:
        score += 0.1
    
    # Penalize for excessive digits
    digit_ratio = len(re.findall(r'\d', s_norm)) / total_chars if total_chars > 0 else 0.0
    if digit_ratio > 0.1:
        score -= 0.3
    
    return max(0.0, min(1.0, score))


def is_plausible_person_name(s: str) -> bool:
    """
    Check if a string is a plausible person name.
    Returns True if name_quality_score >= 0.65.
    
    Strengthened to reject:
    - Known boilerplate (EXECUTED BY, etc.)
    - Gibberish patterns
    - Label-only text
    """
    if not s or not s.strip():
        return False
    
    # Quick blacklist check first (faster)
    s_lower = s.lower()
    quick_blacklist = [
        "executed by", "in witness", "witness whereof", "vendor", "vendee",
        "signature", "witness", "signed", "sealed", "delivered"
    ]
    for token in quick_blacklist:
        if token in s_lower:
            return False
    
    # Special case: 2-word Urdu names (like "کاشف زابد") should pass
    # Check if it's a 2-word Urdu name (common pattern)
    s_norm = normalize_line(s)
    # Include Arabic Presentation Forms for better Urdu detection
    urdu_words = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+', s_norm)
    if len(urdu_words) == 2:
        # Two Urdu words - likely a valid name
        # Check each word is reasonable length (at least 2 chars)
        if all(len(w) >= 2 for w in urdu_words):
            # Check letter ratio is good
            letter_count = len(re.findall(r'[a-zA-Z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', s_norm))
            total_chars = len(s_norm)
            letter_ratio = letter_count / total_chars if total_chars > 0 else 0.0
            if letter_ratio >= 0.5:  # At least 50% letters
                return True
    
    # Check score threshold
    return name_quality_score(s) >= 0.65


def clean_person_name(raw: str) -> str:
    """
    Clean extracted person name by removing CNIC patterns, stop tokens, and leading labels.
    
    Args:
        raw: Raw extracted name string
        
    Returns:
        Cleaned name string suitable for validation
    """
    if not raw:
        return ""
    
    # Normalize whitespace and punctuation
    s = normalize_whitespace(raw)
    
    # Remove CNIC-like patterns (#####-#######-# or 13 digits)
    s = re.sub(r'\d{5}[- ]?\d{7}[- ]?\d{1}', '', s)
    s = re.sub(r'\d{13}', '', s)
    
    # Remove long digit runs (likely not part of name)
    s = re.sub(r'\d{6,}', '', s)
    
    # Remove leading labels (Urdu)
    for label in LEADING_LABELS_URDU:
        # Match label followed by colon, dash, or space
        pattern = rf'^{re.escape(label)}\s*[:،\-]\s*'
        s = re.sub(pattern, '', s, flags=re.IGNORECASE)
        # Also match if label is at start
        if s.startswith(label):
            s = s[len(label):].strip()
            # Remove following colon/dash if present
            s = re.sub(r'^[:،\-]\s*', '', s)
    
    # Remove leading labels (English)
    for label in LEADING_LABELS_EN:
        pattern = rf'^{re.escape(label)}\s*[:,\-]\s*'
        s = re.sub(pattern, '', s, flags=re.IGNORECASE)
        if s.lower().startswith(label.lower()):
            s = s[len(label):].strip()
            s = re.sub(r'^[:,\-]\s*', '', s)
    
    # Truncate at stop tokens (Urdu) - keep only text before first stop token
    for stop_token in STOP_TOKENS_URDU:
        if stop_token in s:
            idx = s.find(stop_token)
            s = s[:idx].strip()
            break
    
    # Truncate at stop tokens (English) - case insensitive
    s_lower = s.lower()
    for stop_token in STOP_TOKENS_EN:
        if stop_token in s_lower:
            idx = s_lower.find(stop_token)
            s = s[:idx].strip()
            break
    
    # Remove remaining excessive punctuation
    s = re.sub(r'[.,;:!?]{2,}', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()


def normalize_line(s: str) -> str:
    """
    Normalize line: collapse whitespace, remove excessive punctuation.
    Preserves Urdu characters.
    """
    # Normalize whitespace
    s = normalize_whitespace(s)
    
    # Remove excessive punctuation (keep single commas, hyphens)
    # Allow Arabic comma (،) and semicolon (؛)
    s = re.sub(r'[.,;:!?]{2,}', ' ', s)  # Multiple punctuation -> space
    s = re.sub(r'\s+', ' ', s)  # Multiple spaces -> single space
    
    return s.strip()


def normalize_for_matching(line: str) -> str:
    """
    Normalize line for matching (section markers, anchors, etc.).
    - Strip/normalize whitespace
    - Remove common OCR punctuation noise
    - Lowercase English
    - Normalize Urdu/Arabic presentation forms (NFKC)
    - Remove punctuation for substring matching
    """
    if not line:
        return ""
    
    # Normalize Unicode (NFKC handles presentation forms)
    s = unicodedata.normalize('NFKC', line)
    
    # Normalize whitespace
    s = normalize_whitespace(s)
    
    # Remove common OCR noise punctuation (keep Arabic comma/semicolon for now)
    s = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF،؛]', '', s)
    
    # Lowercase English characters only (preserve Urdu)
    s = ''.join(c.lower() if ord(c) < 128 and c.isalpha() else c for c in s)
    
    # Final whitespace normalization
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s


def split_possible_names(s: str) -> List[str]:
    """
    Split string on common name delimiters.
    Returns cleaned tokens, stripping titles.
    """
    # Normalize first
    s = normalize_line(s)
    
    # Split on delimiters
    parts = [s]
    for delimiter in NAME_DELIMITERS:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(delimiter))
        parts = new_parts
    
    # Clean each part
    cleaned = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Remove common titles (English)
        title_patterns = [
            r'^(mr|mrs|miss|ms|dr|prof|sir|madam)\.?\s+',
            r'\s+(son|s/o|d/o|w/o|c/o)\s+',
        ]
        for pattern in title_patterns:
            part = re.sub(pattern, ' ', part, flags=re.IGNORECASE)
        
        # Remove common titles (Urdu) - جناب, مسٹر, etc.
        urdu_titles = ['جناب', 'مسٹر', 'مسز', 'ڈاکٹر', 'پروفیسر']
        for title in urdu_titles:
            if part.startswith(title):
                part = part[len(title):].strip()
        
        part = normalize_line(part)
        if part and len(part) >= 3:  # Minimum length
            cleaned.append(part)
    
    return cleaned


def extract_cnic_tokens(text: str) -> List[str]:
    """
    Extract CNIC-like tokens from text using robust digit-based detection.
    Finds CNICs even when OCR drops hyphens/spaces.
    Returns list of normalized CNIC strings (5-7-1 format) in order of first appearance.
    """
    found_cnics = []
    seen_normalized = set()
    
    # Method 1: Standard hyphenated/spaced pattern: \b\d{5}[- ]?\d{7}[- ]?\d\b
    standard_pattern = r'\b\d{5}[- ]?\d{7}[- ]?\d\b'
    for match in re.finditer(standard_pattern, text):
        digits = re.sub(r'\D', '', match.group())
        if len(digits) == 13:
            normalized = f"{digits[0:5]}-{digits[5:12]}-{digits[12:13]}"
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                found_cnics.append(normalized)
    
    # Method 2: Pure 13-digit runs: \b\d{13}\b
    pure_digits_pattern = r'\b\d{13}\b'
    for match in re.finditer(pure_digits_pattern, text):
        digit_seq = match.group()
        normalized = f"{digit_seq[0:5]}-{digit_seq[5:12]}-{digit_seq[12:13]}"
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            found_cnics.append(normalized)
    
    # Method 3: Spaced OCR with multiple spaces around hyphens
    spaced_pattern = r'(\d{5})\s*[- ]?\s*(\d{7})\s*[- ]?\s*(\d)'
    for match in re.finditer(spaced_pattern, text):
        part1, part2, part3 = match.groups()
        normalized = f"{part1}-{part2}-{part3}"
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            found_cnics.append(normalized)
    
    return found_cnics


def is_cnic_like(text: str) -> bool:
    """Check if text contains CNIC-like pattern using digit-based detection."""
    # Extract all digits
    digits_only = re.sub(r'\D', '', text)
    # Check for 13-digit sequence
    if len(digits_only) >= 13:
        return True
    # Also check fuzzy pattern
    fuzzy_pattern = r'(\d{5})\D{0,4}(\d{7})\D{0,4}(\d)'
    return bool(re.search(fuzzy_pattern, text))


@dataclass
class PersonBlock:
    """A person block extracted around a CNIC mention."""
    block_text: str
    page_number: int
    line_index_start: int
    line_index_end: int
    cnic_token: str
    best_name: str


def extract_urdu_labelled_roles_from_page(lines: List[str], page_no: int, doc_id: str = "") -> Dict[str, Tuple[str, int, str]]:
    """
    Extract seller, buyer, and witness from a single page using Urdu labels.
    
    P21: Page-by-page Urdu labelled-field extraction with tolerant matching.
    
    Args:
        lines: List of lines from a single page
        page_no: Page number (for logging)
        doc_id: Document ID (for logging)
    
    Returns:
        Dict with keys 'seller', 'buyer', 'witness', each containing
        (value, page_no, method) tuple if found, else not included
    """
    result = {}
    
    # P21: Normalize lines (light normalization)
    # Handle case where lines may contain \n separators (from OCR text split)
    normalized_lines = []
    for line in lines:
        # If line contains \n, split it into multiple logical lines
        if '\n' in line:
            sub_lines = line.split('\n')
            for sub_line in sub_lines:
                sub_line_norm = normalize_whitespace(sub_line.strip())
                if sub_line_norm:
                    normalized_lines.append(sub_line_norm)
        else:
            # Strip and replace multiple spaces
            line_norm = normalize_whitespace(line.strip())
            if line_norm:
                normalized_lines.append(line_norm)
    
    # Urdu section markers (tolerant patterns)
    seller_markers = ["بائع", "فروشندہ", "نام بائع", "نامِ بائع", "نام مالک", "مالک", "فروخت کنندہ"]
    buyer_markers = ["مشتری", "خریدار", "نام مشتری", "نامِ مشتری", "نام خریدار"]
    witness_markers = ["گواہ", "گواہان", "نام گواہ", "گواہ نمبر", "شاہد"]
    
    # Track which markers were found and their line indices
    urdu_label_hits = {}
    
    # Detect seller block
    for line_idx, line in enumerate(normalized_lines):
        line_normalized = normalize_for_matching(line)
        for marker in seller_markers:
            marker_norm = normalize_for_matching(marker)
            if marker_norm in line_normalized:
                urdu_label_hits["seller"] = line_idx
                # P21: Extract name AFTER the specific marker (marker-specific extraction)
                # Find the position of the marker in the line
                marker_pos = line_normalized.find(marker_norm)
                if marker_pos >= 0:
                    # Extract text after the marker (until next marker or CNIC/end of line)
                    # Look for colon/semicolon after marker, then extract name
                    after_marker = line[marker_pos + len(marker):].strip()
                    # Check for colon/semicolon immediately after marker
                    name_match = re.search(r'[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ|خریدار|مشتری|گواہ)', after_marker, re.IGNORECASE)
                    if name_match:
                        name_candidate = name_match.group(1).strip()
                        # Clean name (remove common prefixes)
                        name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', name_candidate, flags=re.IGNORECASE).strip()
                        # Remove trailing markers that might be in the name
                        name_candidate = re.sub(r'\s*(?:خریدار|مشتری|گواہ|CNIC|شناختی|کارڈ).*$', '', name_candidate, flags=re.IGNORECASE).strip()
                        if name_candidate and len(name_candidate) > 2:
                            is_valid, _ = is_plausible_party_name(name_candidate, role="seller")
                            if is_valid:
                                # P23: Normalize party role value (remove newlines/whitespace)
                                name_candidate = normalize_party_role_value(name_candidate)
                                result["seller"] = (name_candidate, page_no, "label_urdu_page")
                                if PARTY_ROLES_DEBUG:
                                    logger.info(
                                        f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=seller "
                                        f"value=\"{name_candidate[:60]}\" line_idx={line_idx} line_text=\"{line[:80]}\" marker={marker}"
                                    )
                                break
                # If not found on same line after marker, search window i..i+6 for name line
                for offset in range(1, min(7, len(normalized_lines) - line_idx)):
                    candidate_line = normalized_lines[line_idx + offset].strip()
                    if not candidate_line:
                        continue
                    # Prefer lines containing "نام"
                    if "نام" in candidate_line:
                        # Extract name after "نام" or "نام بمعہ ولدیت"
                        name_match = re.search(r'نام\s*(?:بمعہ\s+ولدیت)?\s*[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ)', candidate_line, re.IGNORECASE)
                        if name_match:
                            name_candidate = name_match.group(1).strip()
                        else:
                            # Try to extract name from line (remove common prefixes)
                            name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', candidate_line, flags=re.IGNORECASE).strip()
                            if not name_candidate:
                                name_candidate = candidate_line
                    else:
                        name_candidate = candidate_line
                    
                    # Validate as plausible party name
                    if name_candidate and len(name_candidate) > 2:
                        is_valid, _ = is_plausible_party_name(name_candidate, role="seller")
                        if is_valid:
                            # P23: Normalize party role value (remove newlines/whitespace)
                            name_candidate = normalize_party_role_value(name_candidate)
                            result["seller"] = (name_candidate, page_no, "label_urdu_page")
                            if PARTY_ROLES_DEBUG:
                                logger.info(
                                    f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=seller "
                                    f"value=\"{name_candidate[:60]}\" line_idx={line_idx + offset} line_text=\"{candidate_line[:80]}\""
                                )
                            break
                break
        if "seller" in result:
            break
    
    # Detect buyer block
    for line_idx, line in enumerate(normalized_lines):
        line_normalized = normalize_for_matching(line)
        for marker in buyer_markers:
            marker_norm = normalize_for_matching(marker)
            if marker_norm in line_normalized:
                urdu_label_hits["buyer"] = line_idx
                # P21: Extract name AFTER the specific marker (marker-specific extraction)
                marker_pos = line_normalized.find(marker_norm)
                if marker_pos >= 0:
                    after_marker = line[marker_pos + len(marker):].strip()
                    name_match = re.search(r'[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ|گواہ|فروخت)', after_marker, re.IGNORECASE)
                    if name_match:
                        name_candidate = name_match.group(1).strip()
                        name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', name_candidate, flags=re.IGNORECASE).strip()
                        # Remove trailing markers
                        name_candidate = re.sub(r'\s*(?:گواہ|فروخت|CNIC|شناختی|کارڈ).*$', '', name_candidate, flags=re.IGNORECASE).strip()
                        if name_candidate and len(name_candidate) > 2:
                            is_valid, _ = is_plausible_party_name(name_candidate, role="buyer")
                            if is_valid:
                                # P23: Normalize party role value (remove newlines/whitespace)
                                name_candidate = normalize_party_role_value(name_candidate)
                                result["buyer"] = (name_candidate, page_no, "label_urdu_page")
                                if PARTY_ROLES_DEBUG:
                                    logger.info(
                                        f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=buyer "
                                        f"value=\"{name_candidate[:60]}\" line_idx={line_idx} line_text=\"{line[:80]}\" marker={marker}"
                                    )
                                break
                # If not found on same line after marker, search window i..i+6 for name line
                for offset in range(1, min(7, len(normalized_lines) - line_idx)):
                    candidate_line = normalized_lines[line_idx + offset].strip()
                    if not candidate_line:
                        continue
                    # Prefer lines containing "نام"
                    if "نام" in candidate_line:
                        name_match = re.search(r'نام\s*(?:بمعہ\s+ولدیت)?\s*[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ)', candidate_line, re.IGNORECASE)
                        if name_match:
                            name_candidate = name_match.group(1).strip()
                        else:
                            name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', candidate_line, flags=re.IGNORECASE).strip()
                            if not name_candidate:
                                name_candidate = candidate_line
                    else:
                        name_candidate = candidate_line
                    
                    if name_candidate and len(name_candidate) > 2:
                        is_valid, _ = is_plausible_party_name(name_candidate, role="buyer")
                        if is_valid:
                            # P23: Normalize party role value (remove newlines/whitespace)
                            name_candidate = normalize_party_role_value(name_candidate)
                            result["buyer"] = (name_candidate, page_no, "label_urdu_page")
                            if PARTY_ROLES_DEBUG:
                                logger.info(
                                    f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=buyer "
                                    f"value=\"{name_candidate[:60]}\" line_idx={line_idx + offset} line_text=\"{candidate_line[:80]}\""
                                )
                            break
                break
        if "buyer" in result:
            break
    
    # Detect witness block
    for line_idx, line in enumerate(normalized_lines):
        line_normalized = normalize_for_matching(line)
        for marker in witness_markers:
            marker_norm = normalize_for_matching(marker)
            if marker_norm in line_normalized:
                urdu_label_hits["witness"] = line_idx
                # P21: Extract name AFTER the specific marker (marker-specific extraction)
                marker_pos = line_normalized.find(marker_norm)
                if marker_pos >= 0:
                    after_marker = line[marker_pos + len(marker):].strip()
                    name_match = re.search(r'[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ|Property)', after_marker, re.IGNORECASE)
                    if name_match:
                        name_candidate = name_match.group(1).strip()
                        name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', name_candidate, flags=re.IGNORECASE).strip()
                        # Remove trailing markers
                        name_candidate = re.sub(r'\s*(?:CNIC|شناختی|کارڈ|Property).*$', '', name_candidate, flags=re.IGNORECASE).strip()
                        if name_candidate and len(name_candidate) > 2:
                            is_valid, _ = is_plausible_party_name(name_candidate, role="witness")
                            if is_valid:
                                # P23: Normalize party role value (remove newlines/whitespace)
                                name_candidate = normalize_party_role_value(name_candidate)
                                result["witness"] = (name_candidate, page_no, "label_urdu_page")
                                if PARTY_ROLES_DEBUG:
                                    logger.info(
                                        f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=witness "
                                        f"value=\"{name_candidate[:60]}\" line_idx={line_idx} line_text=\"{line[:80]}\" marker={marker}"
                                    )
                                break
                # If not found on same line after marker, search window i..i+6 for name line
                for offset in range(1, min(7, len(normalized_lines) - line_idx)):
                    candidate_line = normalized_lines[line_idx + offset].strip()
                    if not candidate_line:
                        continue
                    # Prefer lines containing "نام"
                    if "نام" in candidate_line:
                        name_match = re.search(r'نام\s*(?:بمعہ\s+ولدیت)?\s*[:،]\s*(.+?)(?:\n|$|CNIC|شناختی|کارڈ)', candidate_line, re.IGNORECASE)
                        if name_match:
                            name_candidate = name_match.group(1).strip()
                        else:
                            name_candidate = re.sub(r'^(?:نام|نام\s*بمعہ\s+ولدیت)\s*[:،]\s*', '', candidate_line, flags=re.IGNORECASE).strip()
                            if not name_candidate:
                                name_candidate = candidate_line
                    else:
                        name_candidate = candidate_line
                    
                    if name_candidate and len(name_candidate) > 2:
                        is_valid, _ = is_plausible_party_name(name_candidate, role="witness")
                        if is_valid:
                            # P23: Normalize party role value (remove newlines/whitespace)
                            name_candidate = normalize_party_role_value(name_candidate)
                            result["witness"] = (name_candidate, page_no, "label_urdu_page")
                            if PARTY_ROLES_DEBUG:
                                logger.info(
                                    f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_extract role=witness "
                                    f"value=\"{name_candidate[:60]}\" line_idx={line_idx + offset} line_text=\"{candidate_line[:80]}\""
                                )
                            break
                break
        if "witness" in result:
            break
    
    # Log label hits (even if no extraction)
    if PARTY_ROLES_DEBUG and urdu_label_hits:
        logger.info(
            f"PARTY_ROLES_DEBUG: doc_id={doc_id} page={page_no} urdu_label_hits={urdu_label_hits}"
        )
    
    return result


def detect_section_markers(lines: List[str]) -> List[Tuple[int, str]]:
    """
    Detect section markers (seller/buyer/witness headings) in OCR lines.
    Uses normalized substring matching (not regex word boundaries) for Urdu.
    
    Returns:
        List of (line_index, role) tuples where role is 'seller', 'buyer', or 'witness'
    """
    markers = []
    
    # Seller markers (Urdu + English) - use normalized matching
    # Prioritize Urdu markers and section headings, not boilerplate
    seller_markers_urdu = [
        "بائع", "فروخت کنندہ", "بیچنے والا", "مالک", "نام مالک"
    ]
    seller_markers_en = [
        "seller:", "vendor:", "first party:"
    ]
    
    # Buyer markers
    buyer_markers_urdu = [
        "مشتری", "خریدار", "خرید کنندہ", "نام مشتری"
    ]
    buyer_markers_en = [
        "buyer:", "purchaser:", "vendee:", "second party:"
    ]
    
    # Witness markers
    witness_markers_urdu = [
        "گواہان", "گواہ", "گواہ نمبر", "نام گواہ", "شاہد"
    ]
    witness_markers_en = [
        "witness:", "witnesses:"
    ]
    
    for i, line in enumerate(lines):
        # Normalize for matching
        line_normalized = normalize_for_matching(line)
        if not line_normalized or len(line_normalized) < 2:
            continue
        
        # Check Urdu seller markers first (more reliable for Urdu docs)
        for marker in seller_markers_urdu:
            marker_normalized = normalize_for_matching(marker)
            if marker_normalized in line_normalized:
                markers.append((i, "seller"))
                break
        
        # Check English seller markers only if line is short (likely a heading)
        if (i, "seller") not in markers and len(line_normalized) < 50:
            for marker in seller_markers_en:
                marker_normalized = normalize_for_matching(marker)
                if marker_normalized in line_normalized:
                    markers.append((i, "seller"))
                    break
        
        # Check buyer markers
        if (i, "seller") not in markers:
            for marker in buyer_markers_urdu:
                marker_normalized = normalize_for_matching(marker)
                if marker_normalized in line_normalized:
                    markers.append((i, "buyer"))
                    break
            
            if (i, "buyer") not in markers and len(line_normalized) < 50:
                for marker in buyer_markers_en:
                    marker_normalized = normalize_for_matching(marker)
                    if marker_normalized in line_normalized:
                        markers.append((i, "buyer"))
                        break
        
        # Check witness markers
        if (i, "seller") not in markers and (i, "buyer") not in markers:
            for marker in witness_markers_urdu:
                marker_normalized = normalize_for_matching(marker)
                if marker_normalized in line_normalized:
                    markers.append((i, "witness"))
                    break
            
            if (i, "witness") not in markers and len(line_normalized) < 50:
                for marker in witness_markers_en:
                    marker_normalized = normalize_for_matching(marker)
                    if marker_normalized in line_normalized:
                        markers.append((i, "witness"))
                        break
    
    return markers


def score_name_line(line: str) -> float:
    """
    Score a line for likelihood of being a person name.
    Higher score = more likely to be a name.
    Returns negative score for blacklisted labels.
    """
    line_norm = normalize_line(line)
    if not line_norm or len(line_norm) < 3:
        return -100.0
    
    # Blacklisted label phrases (case-insensitive)
    blacklist = [
        "EXECUTED BY", "IN WITNESSWHEREOF", "WITNESS", "VENDOR", "VENDEE",
        "SCHEDULE OF PROPERTY", "SIGNED", "SEALED", "DELIVERED", "PARTY",
        "HEREINAFTER", "CALLED", "DEED", "SALE", "SIGNATURE",
        "نام", "ولدیت", "شناختی کارڈ نمبر"  # Urdu label-only tokens
    ]
    line_upper = line_norm.upper()
    for phrase in blacklist:
        if phrase in line_upper:
            return -100.0
    
    score = 0.0
    
    # Boost: Contains Arabic/Urdu letters (strong indicator)
    if re.search(r'[\u0600-\u06FF]', line_norm):
        score += 15.0
    
    # Penalize: Contains too many digits (not a name)
    digit_ratio = len(re.findall(r'\d', line_norm)) / max(len(line_norm), 1)
    if digit_ratio > 0.1:
        score -= 10.0
    
    # Penalize: Contains common legal/document words
    legal_words = ["party", "vendor", "vendee", "witness", "deed", "sale", "property"]
    for word in legal_words:
        if re.search(rf'\b{word}\b', line_norm, re.IGNORECASE):
            score -= 5.0
    
    # Boost: Has 2+ word tokens with length >= 3
    tokens = line_norm.split()
    long_tokens = [t for t in tokens if len(t) >= 3]
    if len(long_tokens) >= 2:
        score += 5.0
    elif len(long_tokens) == 1 and len(long_tokens[0]) >= 5:
        score += 2.0  # Single long token might be a name
    
    # Penalize: Mostly short tokens (<=2 chars) - strong penalty
    short_tokens = [t for t in tokens if len(t) <= 2]
    if len(short_tokens) > len(tokens) * 0.4:
        score -= 10.0
    
    # Penalize: Heavy punctuation
    punct_ratio = len(re.findall(r'[.,;:!?()\[\]{}"]', line_norm)) / max(len(line_norm), 1)
    if punct_ratio > 0.15:
        score -= 5.0
    
    # Penalize: Contains quotes or brackets (often OCR artifacts)
    if '"' in line_norm or "'" in line_norm or '[' in line_norm or ']' in line_norm:
        score -= 3.0
    
    # Boost: Reasonable length (not too short, not too long)
    if 5 <= len(line_norm) <= 60:
        score += 2.0
    elif len(line_norm) > 60:
        score -= 2.0  # Too long, likely not a name
    
    # Penalize: Looks like OCR garbage (many single letters or fragments)
    if re.search(r'\b[a-z]\s+[a-z]\s+[a-z]', line_norm.lower()):
        score -= 5.0
    
    # Gibberish detector: reject if too many punctuation/symbols or too few letters
    letter_count = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', line_norm))
    total_chars = len(line_norm)
    if total_chars > 0:
        letter_ratio = letter_count / total_chars
        if letter_ratio < 0.3:  # Less than 30% letters
            score -= 10.0
        if total_chars < 4:  # Extremely short
            score -= 5.0
    
    return score


def extract_best_name_from_cnic_window(lines: List[str], cnic_line_idx: int) -> str:
    """
    Extract the best name from a window around a CNIC occurrence.
    Prefers lines containing "نام" / "نام بمعہ ولدیت" or "Name" label.
    Scans lines from cnic_line_idx-6 to cnic_line_idx+2 (clamped).
    Returns the highest-scoring line as name.
    
    Must skip garbage and only consider plausible names.
    """
    window_start = max(0, cnic_line_idx - 6)
    window_end = min(len(lines), cnic_line_idx + 3)
    
    # First pass: look for "نام" / "Name" label lines (prefer Urdu labels)
    name_label_patterns_urdu = [
        r'نام\s*[:،\-]',
        r'نام\s+بمعہ\s+ولدیت',
        r'نام\s+بمع\s+ولدیت',
        r'ولد\s*[:،\-]',
        r'ولدیت\s*[:،\-]',
    ]
    name_label_patterns_en = [
        r'name\s*[:]',
        r'name\s+with\s+father',
    ]
    
    # First pass: prefer Urdu name labels
    for i in range(window_start, window_end):
        if i >= len(lines):
            break
        line = lines[i]
        line_norm = normalize_line(line)
        
        # Check if this is a name label line (Urdu first)
        for pattern in name_label_patterns_urdu:
            if re.search(pattern, line_norm):
                # Extract text after colon/dash
                if ':' in line or '،' in line or '-' in line:
                    parts = re.split(r'[:،\-]', line_norm, 1)
                    if len(parts) > 1:
                        candidate = parts[1].strip()
                        if candidate:
                            cleaned = clean_person_name(candidate)
                            # Use strict plausibility check
                            if cleaned and is_plausible_person_name(cleaned):
                                return cleaned
                # If no colon, check next line
                if i + 1 < window_end:
                    next_line = lines[i + 1]
                    cleaned = clean_person_name(next_line)
                    # Use strict plausibility check
                    if cleaned and is_plausible_person_name(cleaned):
                        return cleaned
        
        # Check English labels (lower priority)
        for pattern in name_label_patterns_en:
            if re.search(pattern, line_norm, re.IGNORECASE):
                # Extract text after colon
                if ':' in line:
                    parts = re.split(r'[:]', line_norm, 1)
                    if len(parts) > 1:
                        candidate = parts[1].strip()
                        if candidate:
                            cleaned = clean_person_name(candidate)
                            # Use strict plausibility check
                            if cleaned and is_plausible_person_name(cleaned):
                                return cleaned
                # If no colon, check next line
                if i + 1 < window_end:
                    next_line = lines[i + 1]
                    cleaned = clean_person_name(next_line)
                    # Use strict plausibility check
                    if cleaned and is_plausible_person_name(cleaned):
                        return cleaned
    
    # Second pass: score-based selection, but only consider plausible names
    best_line = ""
    best_score = -100.0
    
    for i in range(window_start, window_end):
        if i >= len(lines):
            break
        line = lines[i]
        # Skip if line is clearly a label or boilerplate
        line_lower = line.lower()
        line_upper = line.upper()
        # Reject uppercase boilerplate (mostly uppercase = likely boilerplate)
        uppercase_ratio = len(re.findall(r'[A-Z]', line)) / max(len(line), 1)
        if uppercase_ratio > 0.7 and len(line) > 10:
            continue
        # Reject known boilerplate tokens (expanded list)
        boilerplate_tokens = [
            "executed by", "witness", "vendor", "vendee", "signature", "purchaser", "seller",
            "schedule of property", "context so permits", "mean and include", "legal heirs",
            "representatives", "hereinafter", "referred to", "expression shall"
        ]
        if any(token in line_lower for token in boilerplate_tokens):
            continue
        # Reject if line is mostly uppercase boilerplate
        if line_upper == line and len(line) > 5:
            continue
        # Reject if line contains too many English legal words (likely boilerplate)
        legal_word_count = sum(1 for word in ["context", "permits", "requires", "mean", "include", "legal", "heirs", "representatives"] if word in line_lower)
        if legal_word_count >= 3:
            continue
        
        cleaned = clean_person_name(line)
        if not cleaned:
            continue
        
        # Only consider if it passes plausibility check
        if is_plausible_person_name(cleaned):
            score = name_quality_score(cleaned)
            if score > best_score:
                best_score = score
                best_line = cleaned
    
    if best_score >= 0.65:  # Match the threshold in is_plausible_person_name
        return best_line
    
    return ""


def extract_urdu_structured_roles(lines_by_page: List[Tuple[int, List[str]]]) -> Dict[str, List[Tuple[str, int, str]]]:
    """
    Extract seller, buyer, and witness from Urdu structured pages using labeled fields.
    
    Robust parser that handles:
    - Multiple section marker variants (بائع, فریقِ اوّل, فریق اول, etc.)
    - OCR line breaks (label on one line, value on next)
    - Table cell ordering (value before label)
    - Buyer representatives (بذریعہ نمائندہ)
    - Multiple witnesses (گواہ نمبر 1/2)
    
    Args:
        lines_by_page: List of (page_number, lines) tuples
    
    Returns:
        Dict with keys 'seller', 'buyer', 'witness', each containing list of
        (name, page_number, method) tuples where method="label_urdu"
    """
    result = {
        "seller": [],
        "buyer": [],
        "witness": []
    }
    
    # Expanded Urdu section markers (exact and tolerant variants)
    # Note: OCR may distort characters, so we use substring matching with normalization
    seller_section_markers = [
        "بائع", "فریقِ اوّل", "فریق اول", "فریقِ اول", "مالک", "نام مالک",
        "فروخت کنندہ", "فروشندہ", "بیچنے والا", "vendor", "seller"
    ]
    buyer_section_markers = [
        "مشتری", "خریدار", "خرید کنندہ", "نام مشتری",
        "فریقِ دوم", "فریق دوم", "buyer", "purchaser", "vendee"
    ]
    witness_section_markers = [
        "گواہان", "گواپانی", "گواہ", "گواہ نمبر", "نام گواہ", "شاہد", "شہادت",
        "گواہ نمبر 1", "گواہ نمبر 2", "گواہ نمبر 3", "گُوا ار", "witness"
    ]
    
    # Name label patterns (Urdu and English) - more tolerant
    name_label_patterns_urdu = [
        r'نام\s*[:،\-]',
        r'نام\s+بمعہ\s+ولدیت',
        r'نام\s+بمع\s+ولدیت',
        r'ولد\s*[:،\-]',
        r'ولدیت\s*[:،\-]',
        r'نام\s+بمع\s+ولد',
    ]
    name_label_patterns_en = [
        r'name\s*[:]',
        r'name\s+with\s+father',
    ]
    
    # Representative patterns for buyer
    representative_patterns = [
        r'بذریعہ\s+نمائندہ',
        r'جناب',
        r'نمائندہ',
    ]
    
    current_section = None  # 'seller', 'buyer', 'witness', or None
    section_start_line = None
    buyer_representative = None  # Track buyer representative separately
    
    for page_num, lines in lines_by_page:
        current_section = None
        section_start_line = None
        buyer_representative = None
        
        for line_idx, line in enumerate(lines):
            line_normalized = normalize_for_matching(line)
            if not line_normalized:
                continue
            
            # Check if this line is a section marker
            # Use fuzzy matching: check if marker substring exists (OCR-tolerant)
            # Seller section
            for marker in seller_section_markers:
                marker_norm = normalize_for_matching(marker)
                # For short markers, require exact substring match
                # For longer markers, allow partial match
                if len(marker_norm) <= 5:
                    if marker_norm in line_normalized:
                        current_section = "seller"
                        section_start_line = line_idx
                        break
                else:
                    # For longer markers, check if key characters match
                    if marker_norm in line_normalized or any(
                        normalize_for_matching(marker[:i]) in line_normalized 
                        for i in range(3, len(marker) + 1)
                    ):
                        current_section = "seller"
                        section_start_line = line_idx
                        break
            
            # Buyer section
            if current_section != "seller":
                for marker in buyer_section_markers:
                    marker_norm = normalize_for_matching(marker)
                    if len(marker_norm) <= 5:
                        if marker_norm in line_normalized:
                            current_section = "buyer"
                            section_start_line = line_idx
                            break
                    else:
                        if marker_norm in line_normalized or any(
                            normalize_for_matching(marker[:i]) in line_normalized 
                            for i in range(3, len(marker) + 1)
                        ):
                            current_section = "buyer"
                            section_start_line = line_idx
                            break
            
            # Witness section (check for numbered witnesses)
            # More tolerant for witness markers due to OCR errors
            if current_section not in ["seller", "buyer"]:
                for marker in witness_section_markers:
                    marker_norm = normalize_for_matching(marker)
                    # For witness, be very tolerant - check if first 3+ chars match
                    if len(marker_norm) >= 3:
                        marker_prefix = marker_norm[:3]
                        if marker_prefix in line_normalized or marker_norm in line_normalized:
                            current_section = "witness"
                            section_start_line = line_idx
                            break
            
            # If we're in a section, look for name labels
            if current_section:
                # Check if this line contains a name label
                found_label = False
                label_text = ""
                
                # Check Urdu name labels
                for pattern in name_label_patterns_urdu:
                    if re.search(pattern, line_normalized):
                        found_label = True
                        label_text = line
                        break
                
                # Check English name labels (only if line is short, likely a heading)
                if not found_label and len(line_normalized) < 50:
                    for pattern in name_label_patterns_en:
                        if re.search(pattern, line_normalized, re.IGNORECASE):
                            found_label = True
                            label_text = line
                            break
                
                if found_label:
                    # Extract name from this line (after colon) or next line
                    name_candidate = None
                    
                    # Try to extract after colon/dash (handle both orders)
                    colon_match = re.search(r'[:،\-]\s*(.+?)(?:\s*$|[,;])', line)
                    if colon_match:
                        name_candidate = colon_match.group(1).strip()
                    else:
                        # Check if value appears BEFORE label (table cell ordering)
                        # Pattern: name_text followed by label
                        for pattern in name_label_patterns_urdu:
                            match = re.search(r'(.+?)\s+' + pattern, line_normalized)
                            if match:
                                name_candidate = match.group(1).strip()
                                break
                    
                    # If still no candidate, check next non-empty line
                    if not name_candidate and line_idx + 1 < len(lines):
                        next_line = lines[line_idx + 1].strip()
                        if next_line and len(next_line) >= 3:
                            # Skip if next line is another label
                            next_line_norm = normalize_for_matching(next_line)
                            is_next_label = False
                            for pattern in name_label_patterns_urdu + name_label_patterns_en:
                                if re.search(pattern, next_line_norm, re.IGNORECASE):
                                    is_next_label = True
                                    break
                            if not is_next_label:
                                name_candidate = next_line
                    
                    if name_candidate:
                        # Clean and validate the name
                        cleaned = clean_person_name(name_candidate)
                        # For Urdu names, try to extract just the first valid name part if there's OCR garbage
                        if cleaned and not is_plausible_person_name(cleaned):
                            # Try splitting and taking first plausible part
                            parts = cleaned.split()
                            for i in range(len(parts), 0, -1):
                                candidate_part = ' '.join(parts[:i])
                                if is_plausible_person_name(candidate_part):
                                    cleaned = candidate_part
                                    break
                            else:
                                cleaned = None
                        
                        if cleaned and is_plausible_person_name(cleaned):
                            # Add to result (avoid duplicates)
                            existing_names = [n for n, _, _ in result[current_section]]
                            if cleaned not in existing_names:
                                result[current_section].append((cleaned, page_num, "label_urdu"))
                                
                                # For witness, limit to 3
                                if current_section == "witness" and len(result["witness"]) >= 3:
                                    break
                
                # Special handling for buyer representatives
                if current_section == "buyer":
                    for pattern in representative_patterns:
                        if re.search(pattern, line_normalized):
                            # Look for name in same line or next lines
                            if line_idx + 1 < len(lines):
                                next_line = lines[line_idx + 1].strip()
                                if next_line and len(next_line) >= 3:
                                    cleaned = clean_person_name(next_line)
                                    if cleaned and is_plausible_person_name(cleaned):
                                        buyer_representative = cleaned
                            break
                
                # Reset section if we've moved too far (more than 30 lines from section start)
                if section_start_line is not None and line_idx - section_start_line > 30:
                    current_section = None
                    section_start_line = None
        
        # Consolidate buyer with representative if found
        if buyer_representative and result["buyer"]:
            buyer_names = [n for n, _, _ in result["buyer"]]
            if buyer_representative not in buyer_names:
                # Add representative to buyer list
                result["buyer"].append((buyer_representative, page_num, "label_urdu"))
    
    return result


def extract_labelled_fields(lines_by_page: List[Tuple[int, List[str]]]) -> Dict[str, List[Tuple[str, int, str]]]:
    """
    Wrapper for extract_urdu_structured_roles (backward compatibility).
    """
    return extract_urdu_structured_roles(lines_by_page)
    """
    Extract seller, buyer, and witness from Urdu structured pages using labeled fields.
    
    Operates page-by-page and targets Urdu form patterns:
    - Seller: extract from "بائع" section using "نام" / "نام بمعہ ولدیت" labels
    - Buyer: extract from "مشتری" section using same labeled-field approach
    - Witnesses: extract from "گواہان" (or "گواہ نمبر") section; capture up to 3 witnesses
    
    Args:
        lines_by_page: List of (page_number, lines) tuples
    
    Returns:
        Dict with keys 'seller', 'buyer', 'witness', each containing list of
        (name, page_number, label) tuples
    """
    result = {
        "seller": [],
        "buyer": [],
        "witness": []
    }
    
    # Urdu section markers
    seller_section_markers = ["بائع", "فروخت کنندہ", "مالک", "نام مالک"]
    buyer_section_markers = ["مشتری", "خریدار", "خرید کنندہ", "نام مشتری"]
    witness_section_markers = ["گواہان", "گواہ", "گواہ نمبر", "نام گواہ", "شاہد"]
    
    # Name label patterns (Urdu and English)
    name_label_patterns_urdu = [
        r'نام\s*[:،]',
        r'نام\s+بمعہ\s+ولدیت',
        r'نام\s+بمع\s+ولدیت',
    ]
    name_label_patterns_en = [
        r'name\s*[:]',
        r'name\s+with\s+father',
    ]
    
    current_section = None  # 'seller', 'buyer', 'witness', or None
    section_start_line = None
    
    for page_num, lines in lines_by_page:
        current_section = None
        section_start_line = None
        
        for line_idx, line in enumerate(lines):
            line_normalized = normalize_for_matching(line)
            if not line_normalized:
                continue
            
            # Check if this line is a section marker
            # Seller section
            for marker in seller_section_markers:
                marker_norm = normalize_for_matching(marker)
                if marker_norm in line_normalized:
                    current_section = "seller"
                    section_start_line = line_idx
                    break
            
            # Buyer section
            if current_section != "seller":
                for marker in buyer_section_markers:
                    marker_norm = normalize_for_matching(marker)
                    if marker_norm in line_normalized:
                        current_section = "buyer"
                        section_start_line = line_idx
                        break
            
            # Witness section
            if current_section not in ["seller", "buyer"]:
                for marker in witness_section_markers:
                    marker_norm = normalize_for_matching(marker)
                    if marker_norm in line_normalized:
                        current_section = "witness"
                        section_start_line = line_idx
                        break
            
            # If we're in a section, look for name labels
            if current_section:
                # Check if this line contains a name label
                found_label = False
                label_text = ""
                
                # Check Urdu name labels
                for pattern in name_label_patterns_urdu:
                    if re.search(pattern, line_normalized):
                        found_label = True
                        label_text = line
                        break
                
                # Check English name labels (only if line is short, likely a heading)
                if not found_label and len(line_normalized) < 50:
                    for pattern in name_label_patterns_en:
                        if re.search(pattern, line_normalized, re.IGNORECASE):
                            found_label = True
                            label_text = line
                            break
                
                if found_label:
                    # Extract name from this line (after colon) or next line
                    name_candidate = None
                    
                    # Try to extract after colon/dash
                    colon_match = re.search(r'[:،]\s*(.+?)(?:\s*$|[,;])', line)
                    if colon_match:
                        name_candidate = colon_match.group(1).strip()
                    else:
                        # Check next non-empty line
                        if line_idx + 1 < len(lines):
                            next_line = lines[line_idx + 1].strip()
                            if next_line and len(next_line) >= 3:
                                name_candidate = next_line
                    
                    if name_candidate:
                        # Clean and validate the name
                        cleaned = clean_person_name(name_candidate)
                        if cleaned and is_plausible_person_name(cleaned):
                            # Add to result (avoid duplicates)
                            existing_names = [n for n, _, _ in result[current_section]]
                            if cleaned not in existing_names:
                                result[current_section].append((cleaned, page_num, label_text))
                                
                                # For witness, limit to 3
                                if current_section == "witness" and len(result["witness"]) >= 3:
                                    break
                
                # Reset section if we've moved too far (more than 30 lines from section start)
                if section_start_line is not None and line_idx - section_start_line > 30:
                    current_section = None
                    section_start_line = None
    
    return result


def extract_vendor_vendee_structured(combined_text: str) -> Dict[str, Optional[str]]:
    """
    Extract seller and buyer from structured English sale deed pattern:
    "between <seller> ... (hereinafter called ... Vendor) and <buyer> ... (hereinafter called ... Vendee)"
    
    Returns:
        Dict with 'seller' and 'buyer' keys, values are names or None
    """
    result = {"seller": None, "buyer": None}
    
    # Tolerant regex (DOTALL, case-insensitive)
    pattern = re.compile(
        r'between\s+(.+?)\s+\([^)]*hereinafter[^)]*called[^)]*vendor[^)]*\)'
        r'\s+and\s+(.+?)\s+\([^)]*hereinafter[^)]*called[^)]*vendee[^)]*\)',
        re.DOTALL | re.IGNORECASE
    )
    
    match = pattern.search(combined_text)
    if match:
        seller_candidate = match.group(1).strip()
        buyer_candidate = match.group(2).strip()
        
        # Clean and validate seller
        seller_cleaned = clean_person_name(seller_candidate)
        if seller_cleaned and len(seller_cleaned) >= 3:
            # Check score threshold
            if score_name_line(seller_cleaned) > 0:
                is_valid, _ = is_probably_name_line(seller_cleaned)
                if is_valid:
                    result["seller"] = seller_cleaned
        
        # Clean and validate buyer
        buyer_cleaned = clean_person_name(buyer_candidate)
        if buyer_cleaned and len(buyer_cleaned) >= 3:
            # Check score threshold
            if score_name_line(buyer_cleaned) > 0:
                is_valid, _ = is_probably_name_line(buyer_cleaned)
                if is_valid:
                    result["buyer"] = buyer_cleaned
    
    return result


def assign_blocks_to_roles_by_section(
    person_blocks: List[PersonBlock],
    section_markers: List[Tuple[int, str]],
    all_lines: List[str]
) -> Dict[str, List[str]]:
    """
    Assign PersonBlocks to roles based on nearest preceding section marker.
    
    Args:
        person_blocks: List of PersonBlock objects
        section_markers: List of (line_index, role) tuples
        all_lines: Full list of OCR lines for context
    
    Returns:
        Dict with keys 'seller', 'buyer', 'witness' and values as lists of names
    """
    assigned = {"seller": [], "buyer": [], "witness": []}
    
    for block in person_blocks:
        # Find nearest preceding section marker within N=25 lines
        block_center = (block.line_index_start + block.line_index_end) // 2
        nearest_marker = None
        nearest_distance = 25  # Max search distance
        
        for marker_line_idx, marker_role in section_markers:
            if marker_line_idx < block_center:
                distance = block_center - marker_line_idx
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_marker = marker_role
        
        # If found, assign to that role
        if nearest_marker:
            if block.best_name and block.best_name not in assigned[nearest_marker]:
                assigned[nearest_marker].append(block.best_name)
        # If no marker found, skip (will be handled by fallback)
    
    return assigned


def extract_person_block_candidates(
    lines: List[str],
    line_to_page: Dict[int, Tuple[int, str]]
) -> List[PersonBlock]:
    """
    Extract person blocks around CNIC mentions using score-based name selection.
    
    Args:
        lines: List of text lines
        line_to_page: Map from line index to (page_number, original_line)
    
    Returns:
        List of PersonBlock objects
    """
    blocks = []
    seen_cnics = set()  # Deduplicate by CNIC token
    
    for i, line in enumerate(lines):
        if is_cnic_like(line):
            # Extract CNIC token
            cnic_tokens = extract_cnic_tokens(line)
            if not cnic_tokens:
                continue
            
            cnic_token = cnic_tokens[0]
            
            # Skip if we've already seen this CNIC
            if cnic_token in seen_cnics:
                continue
            seen_cnics.add(cnic_token)
            
            # Create block: CNIC line ± 2 lines
            block_start = max(0, i - 2)
            block_end = min(len(lines), i + 3)
            block_lines = lines[block_start:block_end]
            block_text = ' '.join(block_lines)
            
            # Get page number
            page_num, _ = line_to_page.get(i, (1, ""))
            
            # Extract best name using score-based selection
            best_name = extract_best_name_from_cnic_window(lines, i)
            
            # Additional validation: reject if name is clearly garbage
            if best_name:
                # Reject if name is too short, mostly symbols, or matches blacklist
                if len(best_name.strip()) < 3:
                    best_name = ""
                elif re.match(r'^[\d\s\-\(\)\[\]\/\\\.]+$', best_name):
                    best_name = ""
                elif best_name.upper() in ["EXECUTED BY", "WITNESS", "VENDOR", "VENDEE", "SIGNATURE"]:
                    best_name = ""
                # Reject if name has very low letter ratio
                letter_chars = re.sub(r'[^\w\u0600-\u06FF]', '', best_name)
                if len(letter_chars) < len(best_name) * 0.3:
                    best_name = ""
            
            if best_name:
                blocks.append(PersonBlock(
                    block_text=block_text,
                    page_number=page_num,
                    line_index_start=block_start,
                    line_index_end=block_end,
                    cnic_token=cnic_token,
                    best_name=best_name
                ))
    
    return blocks


def extract_names_near_anchor(
    lines: List[str],
    anchor_regex: Pattern,
    lookahead: int = 3,
    validator_func=None
) -> List[Tuple[str, int]]:
    """
    Extract names near anchor patterns.
    
    Args:
        lines: List of text lines
        anchor_regex: Compiled regex pattern for anchor (seller/buyer/witness)
        lookahead: Number of lines to look ahead after anchor
        validator_func: Function to validate name candidates
    
    Returns:
        List of (name, line_index) tuples
    """
    if validator_func is None:
        validator_func = is_probably_name_line
    
    found_names = []
    seen_names = set()
    
    for i, line in enumerate(lines):
        line_normalized = normalize_line(line)
        
        # Check if line contains anchor
        if anchor_regex.search(line_normalized):
            # Try inline extraction: text after ":" or "-"
            inline_match = re.search(r'[:]\s*(.+?)(?:\s*$|[,;])', line_normalized)
            if inline_match:
                candidate = inline_match.group(1).strip()
                # Split if multiple names
                for name_part in split_possible_names(candidate):
                    name_part = normalize_line(name_part)
                    if name_part and len(name_part) >= 3:
                        # Clean the name before validation
                        cleaned = clean_person_name(name_part)
                        if cleaned and is_plausible_person_name(cleaned):
                                normalized = cleaned.lower()
                                if normalized not in seen_names:
                                    found_names.append((cleaned, i))
                                    seen_names.add(normalized)
            
            # If inline not found, look ahead
            if not inline_match:
                for j in range(i + 1, min(i + 1 + lookahead, len(lines))):
                    lookahead_line = normalize_line(lines[j])
                    if not lookahead_line:
                        continue
                    
                    # Skip if line looks like another anchor or label
                    if re.search(r'\b(seller|buyer|witness|vendor|purchaser|فروخت|خریدار|گواہ)\b', lookahead_line, re.IGNORECASE):
                        break
                    
                    # Validate the line as a potential name (use strict plausibility)
                    if is_plausible_person_name(lookahead_line):
                        # Try to extract name parts
                        for name_part in split_possible_names(lookahead_line):
                            name_part = normalize_line(name_part)
                            if name_part and len(name_part) >= 3:
                                # Clean the name before validation
                                cleaned = clean_person_name(name_part)
                                if cleaned and is_plausible_person_name(cleaned):
                                        normalized = cleaned.lower()
                                        if normalized not in seen_names:
                                            found_names.append((cleaned, j))
                                            seen_names.add(normalized)
                                            break  # Take first valid name from this line
    
    return found_names


def extract_party_roles_from_document(pages: List[PageOCR]) -> Dict[str, any]:
    """
    Extract party roles (seller, buyer, witness) from a document's pages.
    
    Args:
        pages: List of PageOCR objects (should be sorted by page_number)
    
    Returns:
        {
            "seller_names": List[str],
            "buyer_names": List[str],
            "witness_names": List[str],
            "evidence": {
                "document_id": str,
                "page_number": int,
                "snippet": str
            }
        }
    """
    if not pages:
        return {
            "seller_names": [],
            "buyer_names": [],
            "witness_names": [],
            "evidence": None
        }
    
    # Combine page texts but keep line order
    all_lines = []
    line_to_page = {}  # Map line index to (page_number, original_line)
    
    for page in pages:
        page_lines = page.text.split('\n')
        for line in page_lines:
            line_stripped = line.strip()
            if line_stripped:
                line_idx = len(all_lines)
                all_lines.append(line_stripped)
                line_to_page[line_idx] = (page.page_number, line_stripped)
    
    combined_text = '\n'.join(all_lines)
    
    # Check if this is a sale deed
    is_sale_deed = detect_sale_deed(combined_text)
    
    # Debug: detect which keywords matched
    matched_keywords = []
    text_normalized = normalize_whitespace(combined_text.lower())
    for keyword in SALE_DEED_KEYWORDS_EN:
        if keyword.lower() in text_normalized:
            matched_keywords.append(keyword)
    for keyword in SALE_DEED_KEYWORDS_URDU:
        if keyword in combined_text:
            matched_keywords.append(keyword)
    
    seller_names = []
    buyer_names = []
    witness_names = []
    evidence_snippet = None
    evidence_page = pages[0].page_number if pages else 1
    evidence_doc_id = pages[0].document_id if pages else ""
    original_filename = pages[0].document_name if pages else ""
    
    # Initialize result lists for debug logging
    seller_results = []
    buyer_results = []
    witness_results = []
    role_method = {}
    anchors_hit = {"seller": 0, "buyer": 0, "witness": 0}
    cnic_count = 0
    section_markers = []  # Will be populated in sale deed section
    person_blocks = []  # Will be populated in sale deed section
    section_markers = []  # Will be populated in sale deed section
    person_blocks = []  # Will be populated in sale deed section
    # P18: Initialize evidence_dict early to avoid UnboundLocalError when referenced in logging
    evidence_dict = None
    
    # NEW PRECEDENCE ORDER:
    # 1) Urdu labelled-field extraction (highest priority)
    # 2) CNIC + labelled-field near-CNIC extraction (second)
    # 3) CNIC blocks assigned by Urdu section markers (third)
    # 4) CNIC fallback by position (fourth)
    # 5) English anchor extraction (LAST, only if candidate passes strict plausibility)
    
    # Initialize all_cnic_tokens for debug logging (used outside is_sale_deed block)
    all_cnic_tokens = []
    
    if is_sale_deed:
        # Prepare lines_by_page for labelled-field extraction
        lines_by_page = []
        current_page = None
        current_lines = []
        for line_idx, (page_num, line_text) in line_to_page.items():
            if current_page != page_num:
                if current_page is not None:
                    lines_by_page.append((current_page, current_lines))
                current_page = page_num
                current_lines = []
            current_lines.append(line_text)
        if current_page is not None:
            lines_by_page.append((current_page, current_lines))
        
        # P21: 0) Page-by-page Urdu labelled-field extraction (HIGHEST PRIORITY)
        # Scan each page individually BEFORE any other method
        for page_num, page_lines in lines_by_page:
            if seller_names and buyer_names and witness_names:
                break  # Stop if all roles found
            page_extracted = extract_urdu_labelled_roles_from_page(page_lines, page_num, evidence_doc_id)
            # Only set role if not already set (do not overwrite once set)
            if "seller" in page_extracted and not seller_names:
                seller_names = [page_extracted["seller"][0]]
                role_method["seller"] = "label_urdu_page"
            if "buyer" in page_extracted and not buyer_names:
                buyer_names = [page_extracted["buyer"][0]]
                role_method["buyer"] = "label_urdu_page"
            if "witness" in page_extracted and not witness_names:
                witness_names = [page_extracted["witness"][0]]
                role_method["witness"] = "label_urdu_page"
        
        # P21: 0.5) Urdu-first assignment: Check for Urdu anchors and assign CNIC blocks accordingly
        # This runs BEFORE labelled-field extraction to prioritize Urdu section markers
        urdu_seller_markers = ["فروشندہ", "بائع", "فروخت کنندہ", "مالک"]
        urdu_buyer_markers = ["مشتری", "خریدار", "خرید کنندہ"]
        urdu_witness_markers = ["گواہان", "گواہ", "گواہ نمبر", "شاہد"]
        
        # Find pages with Urdu section markers
        pages_with_seller_marker = []
        pages_with_buyer_marker = []
        pages_with_witness_marker = []
        
        for page_num, page_lines in lines_by_page:
            page_text_normalized = normalize_for_matching('\n'.join(page_lines))
            for marker in urdu_seller_markers:
                if normalize_for_matching(marker) in page_text_normalized:
                    pages_with_seller_marker.append(page_num)
                    break
            for marker in urdu_buyer_markers:
                if normalize_for_matching(marker) in page_text_normalized:
                    pages_with_buyer_marker.append(page_num)
                    break
            for marker in urdu_witness_markers:
                if normalize_for_matching(marker) in page_text_normalized:
                    pages_with_witness_marker.append(page_num)
                    break
        
        # Extract person blocks first (needed for Urdu-first assignment)
        person_blocks_prelim = extract_person_block_candidates(all_lines, line_to_page)
        
        # Assign person blocks to roles based on Urdu markers
        if pages_with_witness_marker and person_blocks_prelim:
            # If 'گواہان' exists on a page, classify all CNIC/name blocks on that page as witnesses
            witness_blocks = []
            for block in person_blocks_prelim:
                if block.page_number in pages_with_witness_marker:
                    if block.best_name and is_plausible_party_name(block.best_name, role="witness")[0]:
                        witness_blocks.append(block.best_name)
            if witness_blocks and not witness_names:
                witness_names = witness_blocks[:3]
                role_method["witness"] = "urdu_marker_cnic"
                if PARTY_ROLES_DEBUG:
                    logger.info(
                        f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} urdu_first witness_assigned "
                        f"from_pages={pages_with_witness_marker} count={len(witness_names)}"
                    )
        
        if pages_with_buyer_marker and person_blocks_prelim and not buyer_names:
            # Extract buyer from first non-empty name/org line near 'مشتری' marker
            buyer_candidates = []
            for page_num, page_lines in lines_by_page:
                if page_num not in pages_with_buyer_marker:
                    continue
                # Find the line with the marker
                marker_line_idx = None
                for line_idx, line in enumerate(page_lines):
                    line_norm = normalize_for_matching(line)
                    for marker in urdu_buyer_markers:
                        if normalize_for_matching(marker) in line_norm:
                            marker_line_idx = line_idx
                            break
                    if marker_line_idx is not None:
                        break
                
                if marker_line_idx is not None:
                    # Look for name/org in lines after the marker (up to 10 lines)
                    for offset in range(1, min(11, len(page_lines) - marker_line_idx)):
                        candidate_line = page_lines[marker_line_idx + offset].strip()
                        if not candidate_line:
                            continue
                        # Check if it's a plausible name or org
                        if is_plausible_party_name(candidate_line, role="buyer")[0]:
                            # Trim to reasonable length, stop at newline/comma before narrative
                            candidate_cleaned = candidate_line.split('\n')[0].split(',')[0].strip()
                            if len(candidate_cleaned) > 3 and len(candidate_cleaned) < 200:
                                buyer_candidates.append(candidate_cleaned)
                                break
            
            if buyer_candidates:
                buyer_names = [buyer_candidates[0]]
                role_method["buyer"] = "urdu_marker_direct"
                if PARTY_ROLES_DEBUG:
                    logger.info(
                        f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} urdu_first buyer_assigned "
                        f"from_pages={pages_with_buyer_marker} value=\"{buyer_names[0]}\""
                    )
        
        if pages_with_seller_marker and person_blocks_prelim and not seller_names:
            # Extract seller similarly near 'فروشندہ' section
            seller_candidates = []
            for page_num, page_lines in lines_by_page:
                if page_num not in pages_with_seller_marker:
                    continue
                # Find the line with the marker
                marker_line_idx = None
                for line_idx, line in enumerate(page_lines):
                    line_norm = normalize_for_matching(line)
                    for marker in urdu_seller_markers:
                        if normalize_for_matching(marker) in line_norm:
                            marker_line_idx = line_idx
                            break
                    if marker_line_idx is not None:
                        break
                
                if marker_line_idx is not None:
                    # Look for name/org in lines after the marker (up to 10 lines)
                    for offset in range(1, min(11, len(page_lines) - marker_line_idx)):
                        candidate_line = page_lines[marker_line_idx + offset].strip()
                        if not candidate_line:
                            continue
                        # Check if it's a plausible name or org
                        if is_plausible_party_name(candidate_line, role="seller")[0]:
                            candidate_cleaned = candidate_line.split('\n')[0].split(',')[0].strip()
                            if len(candidate_cleaned) > 3 and len(candidate_cleaned) < 200:
                                seller_candidates.append(candidate_cleaned)
                                break
            
            if seller_candidates:
                seller_names = [seller_candidates[0]]
                role_method["seller"] = "urdu_marker_direct"
                if PARTY_ROLES_DEBUG:
                    logger.info(
                        f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} urdu_first seller_assigned "
                        f"from_pages={pages_with_seller_marker} value=\"{seller_names[0]}\""
                    )
        
        # 1) Urdu labelled-field extraction (highest priority, but only if Urdu-first didn't find all)
        if not seller_names or not buyer_names or not witness_names:
            labelled_fields = extract_labelled_fields(lines_by_page)
        else:
            labelled_fields = {"seller": [], "buyer": [], "witness": []}
        
        # Debug: log labelled field extraction results
        if PARTY_ROLES_DEBUG:
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} labelled_fields_seller={len(labelled_fields['seller'])} "
                f"buyer={len(labelled_fields['buyer'])} witness={len(labelled_fields['witness'])}"
            )
            for role in ["seller", "buyer", "witness"]:
                for name, page_num, label in labelled_fields[role]:
                    logger.info(
                        f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} labelled_field role={role} "
                        f"name=\"{name}\" page={page_num} label=\"{label[:50]}\""
                    )
        
        if labelled_fields["seller"]:
            seller_names = [name for name, _, _ in labelled_fields["seller"]]
            role_method["seller"] = "label_urdu"
            # Set evidence from first match
            if labelled_fields["seller"]:
                _, evidence_page, label = labelled_fields["seller"][0]
                evidence_snippet = f"Label: {label}"
        
        if labelled_fields["buyer"]:
            buyer_names = [name for name, _, _ in labelled_fields["buyer"]]
            role_method["buyer"] = "label_urdu"
            if not evidence_snippet and labelled_fields["buyer"]:
                _, evidence_page, label = labelled_fields["buyer"][0]
                evidence_snippet = f"Label: {label}"
        
        if labelled_fields["witness"]:
            witness_names = [name for name, _, _ in labelled_fields["witness"][:3]]
            role_method["witness"] = "label_urdu"
            if not evidence_snippet and labelled_fields["witness"]:
                _, evidence_page, label = labelled_fields["witness"][0]
                evidence_snippet = f"Label: {label}"
        
        # 2) CNIC + labelled-field near-CNIC extraction (if labelled fields didn't find all roles)
        # Reuse person_blocks_prelim if already extracted, otherwise extract now
        if 'person_blocks_prelim' in locals() and person_blocks_prelim:
            person_blocks = person_blocks_prelim
        else:
            person_blocks = extract_person_block_candidates(all_lines, line_to_page)
        cnic_count = len(person_blocks)
        
        # Extract all CNIC tokens for debug
        for block in person_blocks:
            if block.cnic_token not in all_cnic_tokens:
                all_cnic_tokens.append(block.cnic_token)
        
        # 3) CNIC blocks assigned by Urdu section markers
        section_markers = detect_section_markers(all_lines)
        
        # Debug: log all section markers
        if PARTY_ROLES_DEBUG:
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} section_markers_total={len(section_markers)}"
            )
            for marker_line_idx, marker_role in section_markers:
                marker_line_text = all_lines[marker_line_idx] if marker_line_idx < len(all_lines) else ""
                logger.info(
                    f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} section_marker role={marker_role} "
                    f"line_idx={marker_line_idx} line_text=\"{marker_line_text[:100]}\""
                )
        
        # Filter to only Urdu section markers (not English boilerplate)
        urdu_marker_keywords = ["بائع", "مشتری", "گواہان", "گواہ", "فروخت کنندہ", "خریدار", "مالک"]
        urdu_markers = []
        for m in section_markers:
            if m[0] < len(all_lines):
                line_text = normalize_for_matching(all_lines[m[0]])
                for urdu_keyword in urdu_marker_keywords:
                    if normalize_for_matching(urdu_keyword) in line_text:
                        urdu_markers.append(m)
                        break
        
        # Debug: log filtered Urdu markers
        if PARTY_ROLES_DEBUG:
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} urdu_markers_count={len(urdu_markers)}"
            )
        
        if urdu_markers and person_blocks:
            section_assigned_urdu = assign_blocks_to_roles_by_section(person_blocks, urdu_markers, all_lines)
            # Only use if we don't already have results from labelled fields
            if not seller_names and section_assigned_urdu["seller"]:
                # Filter to only plausible names
                valid_seller = [n for n in section_assigned_urdu["seller"] if is_plausible_person_name(n)]
                if valid_seller:
                    seller_names = valid_seller
                    role_method["seller"] = "section_cnic"
            if not buyer_names and section_assigned_urdu["buyer"]:
                valid_buyer = [n for n in section_assigned_urdu["buyer"] if is_plausible_person_name(n)]
                if valid_buyer:
                    buyer_names = valid_buyer
                    role_method["buyer"] = "section_cnic"
            if not witness_names and section_assigned_urdu["witness"]:
                valid_witness = [n for n in section_assigned_urdu["witness"][:3] if is_plausible_person_name(n)]
                if valid_witness:
                    witness_names = valid_witness
                    role_method["witness"] = "section_cnic"
        
        # 4) CNIC fallback by page order (if still missing roles)
        if person_blocks and (not seller_names or not buyer_names or not witness_names):
            # Filter person blocks to only those with valid names
            valid_blocks = [b for b in person_blocks if b.best_name and is_plausible_person_name(b.best_name)]
            
            # P21: Group blocks by page for better assignment
            blocks_by_page = {}
            for block in valid_blocks:
                if block.page_number not in blocks_by_page:
                    blocks_by_page[block.page_number] = []
                blocks_by_page[block.page_number].append(block)
            
            # P21: Log CNIC blocks by page
            if PARTY_ROLES_DEBUG:
                cnic_blocks_by_page_str = {str(k): len(v) for k, v in blocks_by_page.items()}
                logger.info(
                    f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} cnic_blocks_by_page={cnic_blocks_by_page_str}"
                )
            
            # P21: If >=2 blocks on same page (often page 1), assign by order on that page
            page_1_blocks = blocks_by_page.get(1, [])
            if len(page_1_blocks) >= 2 and (not seller_names or not buyer_names):
                # Sort by line index to preserve order
                page_1_blocks_sorted = sorted(page_1_blocks, key=lambda b: b.line_index_start)
                if not seller_names and page_1_blocks_sorted:
                    seller_from_block = page_1_blocks_sorted[0].best_name
                    seller_names = [seller_from_block]
                    role_method["seller"] = "cnic_page_order"
                    if PARTY_ROLES_DEBUG:
                        logger.info(
                            f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} assign_by_page_order page=1 "
                            f"seller_from_block=\"{seller_from_block}\""
                        )
                if not buyer_names and len(page_1_blocks_sorted) >= 2:
                    buyer_from_block = page_1_blocks_sorted[1].best_name
                    buyer_names = [buyer_from_block]
                    role_method["buyer"] = "cnic_page_order"
                    if PARTY_ROLES_DEBUG:
                        logger.info(
                            f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} assign_by_page_order page=1 "
                            f"buyer_from_block=\"{buyer_from_block}\""
                        )
            
            # P21: Fallback to position-based assignment if page-order didn't work
            if not seller_names and valid_blocks:
                seller_names = [valid_blocks[0].best_name]
                role_method["seller"] = "cnic_fallback"
            if not buyer_names and len(valid_blocks) >= 2:
                buyer_names = [valid_blocks[1].best_name]
                role_method["buyer"] = "cnic_fallback"
            if not witness_names and len(valid_blocks) >= 3:
                witness_candidates = [b.best_name for b in valid_blocks[2:] if b.best_name and is_plausible_person_name(b.best_name)]
                witness_names = witness_candidates[:3]
                if witness_names:
                    role_method["witness"] = "cnic_fallback"
        
        # 5) English anchor extraction (LAST, only if candidate passes strict plausibility)
        # Only run if we still don't have all roles
        if not seller_names or not buyer_names or not witness_names:
            # Seller anchors
            seller_pattern = re.compile(
                r'(?:^|\s)(?:seller|vendor|first\s+party|Vendor|Seller|First\s+Party|'
                r'فروخت\s*کنندہ|بائع|فروشندہ|فریق\s*اول|پہلا\s*فریق|مالک|نام\s*مالک)(?:\s|:|،|$)',
                re.IGNORECASE
            )
            seller_results = extract_names_near_anchor(all_lines, seller_pattern, lookahead=5)
            anchors_hit["seller"] = len(seller_results)
            if not seller_names:
                for name, _ in seller_results:
                    cleaned = clean_person_name(name)
                    if cleaned and is_plausible_person_name(cleaned):
                        seller_names = [cleaned]
                        role_method["seller"] = "anchor"
                        break
            
            # Buyer anchors
            buyer_pattern = re.compile(
                r'(?:^|\s)(?:buyer|purchaser|vendee|second\s+party|Buyer|Purchaser|Vendee|Second\s+Party|'
                r'خریدار|مشتری|فریق\s*دوم|دوسرا\s*فریق)(?:\s|:|،|$)',
                re.IGNORECASE
            )
            buyer_results = extract_names_near_anchor(all_lines, buyer_pattern, lookahead=5)
            anchors_hit["buyer"] = len(buyer_results)
            if not buyer_names:
                for name, _ in buyer_results:
                    cleaned = clean_person_name(name)
                    if cleaned and is_plausible_person_name(cleaned):
                        buyer_names = [cleaned]
                        role_method["buyer"] = "anchor"
                        break
            
            # Witness anchors
            witness_pattern = re.compile(
                r'(?:^|\s)(?:witness|witnesses|attesting\s+witness|Witness|Witnesses|Attesting\s+Witness|'
                r'گواہ|گواہان|شاہد|شاہدین|گواہ\s*نمبر|نام\s*گواہ)(?:\s|:|،|$)',
                re.IGNORECASE
            )
            witness_results = extract_names_near_anchor(all_lines, witness_pattern, lookahead=12)
            anchors_hit["witness"] = len(witness_results)
            if not witness_names:
                witness_candidates = []
                for name, _ in witness_results:
                    cleaned = clean_person_name(name)
                    if cleaned and is_plausible_person_name(cleaned):
                        witness_candidates.append(cleaned)
                        if len(witness_candidates) >= 3:
                            break
                if witness_candidates:
                    witness_names = witness_candidates
                    role_method["witness"] = "anchor"
    
    # Format output: join multiple names with "; " (semicolon separator for single candidate)
    # Deduplicate while preserving order
    def dedupe_preserve_order(names: List[str]) -> List[str]:
        seen = set()
        result = []
        for name in names:
            normalized = name.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(name)
        return result
    
    seller_names_deduped = dedupe_preserve_order(seller_names)
    buyer_names_deduped = dedupe_preserve_order(buyer_names)
    witness_names_deduped = dedupe_preserve_order(witness_names)
    
    # P21: Empty extraction root-cause debug (for missing roles)
    if PARTY_ROLES_DEBUG and is_sale_deed:
        # Calculate stats for empty extraction reasons
        label_urdu_pages_scanned = len(lines_by_page) if is_sale_deed else 0
        label_urdu_found_any = False
        # Check if any page had Urdu label hits (from extract_urdu_labelled_roles_from_page)
        # This will be logged by that function, but we can check by scanning pages
        for page_num, page_lines in lines_by_page:
            page_text_normalized = normalize_for_matching('\n'.join(page_lines))
            seller_markers = ["بائع", "فروشندہ", "نام بائع", "نامِ بائع", "نام مالک", "مالک", "فروخت کنندہ"]
            buyer_markers = ["مشتری", "خریدار", "نام مشتری", "نامِ مشتری", "نام خریدار"]
            witness_markers = ["گواہ", "گواہان", "نام گواہ", "گواہ نمبر", "شاہد"]
            for marker_list in [seller_markers, buyer_markers, witness_markers]:
                for marker in marker_list:
                    if normalize_for_matching(marker) in page_text_normalized:
                        label_urdu_found_any = True
                        break
                if label_urdu_found_any:
                    break
            if label_urdu_found_any:
                break
        
        person_blocks_total = len(person_blocks) if is_sale_deed and 'person_blocks' in locals() else 0
        person_blocks_plausible = len([b for b in person_blocks if b.best_name and is_plausible_person_name(b.best_name)]) if is_sale_deed and 'person_blocks' in locals() else 0
        
        # Pages sample (first 2 lines per page)
        pages_sample = {}
        for page_num, page_lines in lines_by_page[:3]:  # First 3 pages
            first_2_lines = '\n'.join(page_lines[:2]) if len(page_lines) >= 2 else '\n'.join(page_lines)
            pages_sample[page_num] = first_2_lines[:200]  # Limit length
        
        # Log missing roles with reasons
        for role, names_list in [
            ("seller", seller_names_deduped),
            ("buyer", buyer_names_deduped),
            ("witness", witness_names_deduped)
        ]:
            if not names_list:
                missing_reasons = {
                    'label_urdu_pages_scanned': label_urdu_pages_scanned,
                    'label_urdu_found_any': label_urdu_found_any,
                    'cnic_tokens_total': len(all_cnic_tokens),
                    'person_blocks_total': person_blocks_total,
                    'person_blocks_plausible': person_blocks_plausible,
                    'pages_sample': pages_sample
                }
                logger.info(
                    f"PARTY_ROLES_DEBUG: doc_id={evidence_doc_id} missing_role={role} reasons={missing_reasons}"
                )
    
    # DEBUG logging (if enabled)
    if PARTY_ROLES_DEBUG:
        doc_id = pages[0].document_id if pages else "unknown"
        total_pages = len(pages) if pages else 0
        
        # Log per role with reason
        for role, names_list in [
            ("seller", seller_names_deduped),
            ("buyer", buyer_names_deduped),
            ("witness", witness_names_deduped)
        ]:
            method = role_method.get(role, "none")
            reason = "none"
            if not names_list:
                if anchors_hit[role] == 0 and cnic_count == 0:
                    reason = "no_anchors_no_cnic"
                elif anchors_hit[role] == 0:
                    reason = "no_anchors"
                elif cnic_count == 0:
                    reason = "no_cnic_blocks"
                else:
                    reason = "validation_rejected"
            else:
                reason = method if method else "unknown"
            
            extracted_str = "; ".join(names_list) if names_list else ""
            # P16: Include method and page number in per-role log
            method = role_method.get(role, "none")
            evidence_page_num = evidence_page if evidence_dict and evidence_dict.get("page_number") else "unknown"
            if not names_list:
                # P16: Log SKIP with reason when validation rejects
                logger.info(
                    f"PARTY_ROLES_DEBUG: SKIP role={role} doc_id={doc_id} reason={reason} "
                    f"anchors={anchors_hit[role]} cnic_blocks={cnic_count} method={method}"
                )
            else:
                logger.info(
                    f"PARTY_ROLES_DEBUG: doc_id={doc_id} role={role} method={method} page={evidence_page_num} "
                    f"anchors={anchors_hit[role]} cnic_blocks={cnic_count} extracted=\"{extracted_str}\" reason={reason}"
                )
        
        # Log section markers (already logged above, but keep for consistency)
        if section_markers and PARTY_ROLES_DEBUG:
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={doc_id} section_markers_count={len(section_markers)}"
            )
        
        # Log PersonBlocks
        for i, block in enumerate(person_blocks):
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={doc_id} person_block idx={i} "
                f"line_range=[{block.line_index_start},{block.line_index_end}] "
                f"page={block.page_number} name=\"{block.best_name}\" "
                f"cnic=\"{block.cnic_token}\""
            )
        
        # Log document-level summary with CNIC tokens
        all_cnic_tokens_str = ", ".join(all_cnic_tokens) if all_cnic_tokens else "none"
        # P23: Normalize final values before logging and returning
        final_seller = "; ".join(seller_names_deduped) if seller_names_deduped else "none"
        final_buyer = "; ".join(buyer_names_deduped) if buyer_names_deduped else "none"
        final_witness = "; ".join(witness_names_deduped) if witness_names_deduped else "none"
        # Normalize party role values (remove newlines/whitespace)
        final_seller = normalize_party_role_value(final_seller) if final_seller != "none" else final_seller
        final_buyer = normalize_party_role_value(final_buyer) if final_buyer != "none" else final_buyer
        final_witness = normalize_party_role_value(final_witness) if final_witness != "none" else final_witness
        
        # P16: Final summary log (one line per doc) - include pages_used count
        pages_used_count = len(set(p.page_number for p in pages)) if pages else 0
        logger.info(
            f"PARTY_ROLES_DEBUG: doc_id={doc_id} filename=\"{original_filename}\" "
            f"pages_used={pages_used_count} total_pages={total_pages} is_sale_deed={is_sale_deed} "
            f"matched_keywords={matched_keywords} cnic_count={cnic_count} "
            f"cnic_tokens=[{all_cnic_tokens_str}] person_blocks_created={len(person_blocks)} "
            f"section_markers_count={len(section_markers)} "
            f"final_seller=\"{final_seller[:50]}\" method_seller={role_method.get('seller', 'none')} "
            f"final_buyer=\"{final_buyer[:50]}\" method_buyer={role_method.get('buyer', 'none')} "
            f"final_witness=\"{final_witness[:50]}\" method_witness={role_method.get('witness', 'none')}"
        )
        
        # P23: Log normalized values (already normalized above, just log them)
        if PARTY_ROLES_DEBUG:
            logger.info(
                f"PARTY_ROLES_DEBUG: doc_id={doc_id} normalized_values "
                f"seller=\"{final_seller[:60]}\" buyer=\"{final_buyer[:60]}\" witness=\"{final_witness[:60]}\""
            )
    
    # Always return evidence if we have any extracted names or metadata
    evidence_dict = None
    if seller_names_deduped or buyer_names_deduped or witness_names_deduped or role_method:
        evidence_dict = {
            "document_id": evidence_doc_id,
            "page_number": evidence_page,
            "snippet": evidence_snippet or "",
            "role_method": role_method,
            "cnic_count": cnic_count,
            "anchors_hit": anchors_hit,
        }
    
    # P23: Normalize final return values (before validation and returning)
    seller_names_normalized = normalize_party_role_value("; ".join(seller_names_deduped)) if seller_names_deduped else ""
    buyer_names_normalized = normalize_party_role_value("; ".join(buyer_names_deduped)) if buyer_names_deduped else ""
    witness_names_normalized = normalize_party_role_value("; ".join(witness_names_deduped)) if witness_names_deduped else ""
    
    result = {
        "seller_names": seller_names_normalized,
        "buyer_names": buyer_names_normalized,
        "witness_names": witness_names_normalized,
        "evidence": evidence_dict,
        # Include names_list in metadata for structure preservation
        "names_list": {
            "seller": seller_names_deduped,
            "buyer": buyer_names_deduped,
            "witness": witness_names_deduped,
        }
    }
    
    return result


# Unit-style helper for testing plausibility (can be called in __main__ or debug mode)
def test_plausibility_assertions():
    """Test plausibility assertions for common cases."""
    assert is_plausible_person_name("کاشف زابد") == True, "کاشف زابد should be plausible"
    assert is_plausible_person_name("EXECUTED BY") == False, "EXECUTED BY should be rejected"
    assert is_plausible_person_name("De eo re") == False, "De eo re should be rejected"
    assert is_plausible_person_name("Muhammad Ali") == True, "Muhammad Ali should be plausible"
    return True


if __name__ == "__main__":
    # Run plausibility tests
    try:
        test_plausibility_assertions()
        print("All plausibility assertions passed")
    except AssertionError as e:
        print(f"Plausibility assertion failed: {e}")

