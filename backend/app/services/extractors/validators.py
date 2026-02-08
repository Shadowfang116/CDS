"""
P14: Field validators to reduce garbage extraction candidates.
Deterministic, explainable, fast validators for field-specific formats.
"""
import re
from typing import Tuple, Optional


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace in string."""
    return re.sub(r'\s+', ' ', s).strip()


def is_plausible_party_name(s: str, role: str = "person") -> Tuple[bool, Optional[str]]:
    """
    Validate if string is likely a party name (person or organization).
    
    Args:
        s: String to validate
        role: "person", "seller", "buyer", or "witness"
            - "person" or "witness": strict person name validation
            - "seller" or "buyer": allows organization names
    
    Returns:
        Tuple of (is_valid, warning_reason_if_weak)
    """
    s = normalize_whitespace(s)
    
    # CRITICAL: Hard reject corrupted text FIRST (before ANY other logic)
    # This must run before role-aware allowances for org names
    from app.services.ocr_text_quality import is_text_corrupted, detect_mojibake
    
    # Check 1: General corruption detection
    is_corrupted, corruption_reason = is_text_corrupted(s, expected_urdu=False)
    if is_corrupted:
        return False, f"corrupted/mojibake: {corruption_reason}"
    
    # Check 2: Specific mojibake detection (stricter threshold for names)
    is_mojibake, mojibake_ratio, mojibake_count, total_chars = detect_mojibake(s)
    if is_mojibake or mojibake_ratio > 0.01:  # Even 1% is suspicious for names
        return False, f"corrupted/mojibake: ratio={mojibake_ratio:.3f} count={mojibake_count}/{total_chars}"
    
    # Check 3: Specific mojibake characters (additional safety check - must match detect_mojibake)
    mojibake_chars = [
        "╪", "┘", "┌", "▒", "█", "▓", "⌐", "º", "┤", "ü", "¿", "»",  # From user's example
        "║", "╔", "╗", "╚", "╝", "═", "╬", "╩", "╦", "╠", "╣", "╤", "╧", "╥", "╨",
        "╙", "╘", "╒", "╓", "╕", "╖", "╛", "╜", "╞", "╟", "╡", "╢", "╫", "╭", "╮",
        "╯", "╰", "╱", "╲", "╳", "╴", "╵", "╶", "╷", "╸", "╹", "╺", "╻", "╼", "╽", "╾", "╿",
        "┐", "└", "├", "┬", "┴", "┼", "░",  # Additional box drawing
    ]
    for char in mojibake_chars:
        if char in s:
            return False, f"corrupted/mojibake: contains '{char}'"
    
    # Hard reject: too long (likely narrative)
    if len(s) > 120:  # Increased for org names
        return False, "Too long for a name (likely narrative)"
    
    # Hard reject: too short
    if len(s) < 3:
        return False, "Too short for a name (minimum 3 characters)"
    
    # Organization keywords (allowed for seller/buyer)
    org_keywords = [
        "bank", "ltd", "limited", "pvt", "private", "company", "co", "corp", "corporation",
        "society", "association", "trust", "foundation", "group", "holdings",
        "بینک", "لمیٹڈ", "پرائیویٹ", "کمپنی", "کارپوریشن", "سوسائٹی", "ٹرسٹ"
    ]
    
    # Check if this looks like an organization name
    is_org_like = any(keyword.lower() in s.lower() for keyword in org_keywords)
    
    # P16: Hard blocklist for witness role - reject any org names
    if role == "witness":
        # Witness-specific org blocklist (English + Urdu)
        witness_org_blocklist = [
            "THE BANK OF", "BANK", "LIMITED", "PVT", "COMPANY", "BRANCH", "ACT",
            "بینک", "لمیٹڈ", "کمپنی", "برانچ", "بینک آف", "کمپنی لمیٹڈ"
        ]
        s_upper = s.upper()
        for org_term in witness_org_blocklist:
            if org_term in s_upper or org_term in s:
                return False, f"witness role: contains org term '{org_term}'"
        
        # Also reject if contains org keywords (witness must be person)
        if is_org_like:
            return False, "witness role: appears to be organization (only persons allowed)"
    
    # For seller/buyer, allow org names if they're long enough and contain org keywords
    if role in ["seller", "buyer"] and is_org_like:
        # Org names can be longer, but still reject if too narrative-like
        if len(s) > 200:
            return False, "Too long even for organization name"
        
        # Still reject if contains narrative phrases
        narrative_phrases_en = [
            "executed by", "in witness", "witness whereof", "witnesses named",
            "appears", "vide", "in this regard", "competent", "lawful",
        ]
        s_lower = s.lower()
        for phrase in narrative_phrases_en:
            if phrase in s_lower:
                return False, f"Contains narrative phrase: '{phrase}'"
        
        # Org names can have more punctuation (commas, periods in abbreviations)
        # But still reject if too many sentence-ending punctuation
        if s.count('.') > 5 or s.count('!') > 0 or s.count('?') > 0:
            return False, "Too many sentence-ending punctuation marks"
        
        # Allow org names with reasonable letter ratio (more lenient)
        def compute_letter_ratio(text: str) -> float:
            s2 = "".join(ch for ch in text if not ch.isspace())
            if not s2:
                return 0.0
            letters = sum(1 for ch in s2 if ch.isalpha())
            return letters / len(s2)
        
        letter_ratio = compute_letter_ratio(s)
        if letter_ratio < 0.50:  # More lenient for org names
            return False, f"Low letter ratio for organization name ({letter_ratio:.2f} < 0.50)"
        
        return True, "Organization name (seller/buyer allowed)"
    
    # For person names (including witness), use strict validation
    return is_probably_name_line(s)


def is_probably_name_line(s: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if string is likely a name (not narrative).
    Supports both Latin (English) and Arabic script (Urdu) names.
    Returns: (is_valid, warning_reason_if_weak)
    
    Hard rejects narrative sentences.
    """
    s = normalize_whitespace(s)
    
    # Hard reject: too long (likely narrative)
    if len(s) > 80:  # Increased for Urdu names which can be longer
        return False, "Too long for a name (likely narrative)"
    
    # Hard reject: too short
    if len(s) < 3:
        return False, "Too short for a name (minimum 3 characters)"
    
    # Unicode-aware Arabic script detection
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
    
    # Detect script types
    has_arabic = any(is_arabic_char(c) for c in s)
    has_latin = any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in s)
    is_pure_arabic_script = has_arabic and not has_latin
    
    # Hard reject: contains narrative verbs/phrases (English)
    narrative_phrases_en = [
        "appears", "vide", "in this regard", "property", "competent", "owner",
        "letter", "reference", "submitted", "documents", "above mentioned",
        "lawful", "according", "respect", "regard", "hereby", "whereas",
        "therefore", "aforesaid", "aforementioned", "aforesaid property",
        "executed by", "in witness", "witness whereof", "witnesses named",
    ]
    # Urdu narrative phrases (only phrases that are clearly narrative, not common name words)
    narrative_phrases_urdu = [
        "ولد", "ساکن", "ضلع", "تحصیل", "شناختی", "کارڈ", "نمبر",
        "مکان", "پلاٹ", "رہائشی", "اور", "یا",
        "بیع", "فروخت", "خریداری", "فروخت کنندہ", "خریدار",
        # Note: "کا", "کی", "کے" removed - too common in names
    ]
    
    s_lower = s.lower()
    for phrase in narrative_phrases_en:
        if phrase in s_lower:
            return False, f"Contains narrative phrase: '{phrase}'"
    
    for phrase in narrative_phrases_urdu:
        if phrase in s:
            return False, f"Contains narrative phrase: '{phrase}'"
    
    # Hard reject: contains sentence punctuation (allow hyphen in names, allow Arabic comma)
    # Arabic comma (،) and semicolon (؛) are allowed in names
    s_without_arabic_punct = s.replace('،', '').replace('؛', '')
    if re.search(r'[.,;:!?]', s_without_arabic_punct):
        # Allow hyphen (common in names like "Muhammad-Ali")
        if re.search(r'[.,;:!?]', s_without_arabic_punct.replace('-', '')):
            return False, "Contains sentence punctuation (likely narrative)"
    
    # Hard reject: contains too many digits (>20% of characters)
    digit_count = sum(1 for c in s if c.isdigit())
    total_non_space = len([c for c in s if not c.isspace()])
    if total_non_space > 0:
        digit_ratio = digit_count / total_non_space
        if digit_ratio > 0.2:
            return False, f"Too many digits ({digit_ratio:.1%} > 20%)"
    
    # Token count validation (more lenient for Urdu)
    tokens = s.split()
    token_count = len(tokens)
    
    if token_count < 1:
        return False, "Too few tokens for a name (minimum 1)"
    if token_count > 8:  # Increased for Urdu names which can have more tokens
        return False, "Too many tokens for a name (maximum 8)"
    
    # Unicode-aware letter ratio calculation
    def compute_letter_ratio(text: str) -> float:
        """Compute letter ratio using Unicode-aware isalpha()."""
        s2 = "".join(ch for ch in text if not ch.isspace())
        if not s2:
            return 0.0
        letters = sum(1 for ch in s2 if ch.isalpha())  # Unicode-aware
        return letters / len(s2)
    
    letter_ratio = compute_letter_ratio(s)
    
    # Set thresholds based on script type
    default_min_ratio = 0.70
    arabic_min_ratio = 0.45  # More lenient for pure Arabic-script names
    
    min_ratio = arabic_min_ratio if is_pure_arabic_script else default_min_ratio
    
    if letter_ratio < min_ratio:
        # Enhanced error message with diagnostic info
        name_preview = s[:60] if len(s) <= 60 else s[:57] + "..."
        return False, (
            f"Low letter ratio ({letter_ratio:.2f} < {min_ratio:.2f}) "
            f"[has_arabic={has_arabic}, has_latin={has_latin}, "
            f"preview: {name_preview}]"
        )
    
    # Weak warning: very short or very long within acceptable range
    if len(s) < 5:
        return True, "Very short name (may be incomplete)"
    if len(s) > 60:
        return True, "Long name (verify it's not narrative)"
    
    return True, None


def validate_cnic(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate Pakistan CNIC format.
    Returns: (is_valid, normalized_value, warning_reason_if_weak)
    
    Accepts: #####-#######-# or 13 digits
    Normalizes to: #####-#######-#
    """
    s = normalize_whitespace(s)
    
    # Remove common prefixes
    s = re.sub(r'^(cnic|nic|id)\s*[:]?\s*', '', s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Pattern 1: #####-#######-#
    pattern1 = re.match(r'^(\d{5})-(\d{7})-(\d{1})$', s)
    if pattern1:
        normalized = f"{pattern1.group(1)}-{pattern1.group(2)}-{pattern1.group(3)}"
        return True, normalized, None
    
    # Pattern 2: 13 digits (no dashes)
    pattern2 = re.match(r'^(\d{13})$', s)
    if pattern2:
        # Insert dashes
        normalized = f"{s[0:5]}-{s[5:12]}-{s[12:13]}"
        return True, normalized, None
    
    # Pattern 3: 13 digits with spaces/dots
    pattern3 = re.sub(r'[\s.\-]', '', s)
    if re.match(r'^\d{13}$', pattern3):
        normalized = f"{pattern3[0:5]}-{pattern3[5:12]}-{pattern3[12:13]}"
        return True, normalized, "Normalized from spaced format"
    
    return False, None, "Invalid CNIC format (expected #####-#######-# or 13 digits)"


def validate_plot(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate plot number.
    Accepts: "Plot No. 12", "Plot #12", "12"
    Returns: (is_valid, normalized_value, warning_reason_if_weak)
    """
    s = normalize_whitespace(s)
    
    # Remove common prefixes
    s = re.sub(r'^(plot|plot\s*no\.?|plot\s*#|plot\s*number)\s*[:]?\s*', '', s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Extract numeric part
    match = re.search(r'(\d+)', s)
    if not match:
        return False, None, "No numeric plot number found"
    
    plot_num = match.group(1)
    
    # Validate range (1-9999)
    try:
        num = int(plot_num)
        if num < 1 or num > 9999:
            return False, None, f"Plot number out of range (1-9999): {num}"
    except ValueError:
        return False, None, "Invalid plot number format"
    
    return True, plot_num, None


def validate_khasra_list(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate khasra number list.
    Accepts: "123/4, 125/1", "123/4", "123-4"
    Returns: (is_valid, normalized_value, warning_reason_if_weak)
    """
    s = normalize_whitespace(s)
    
    # Pattern: number/number or number-number
    khasra_pattern = r'\d+[/-]\d+'
    matches = re.findall(khasra_pattern, s)
    
    if not matches:
        return False, None, "No valid khasra format found (expected number/number)"
    
    # Normalize to use forward slash
    normalized_list = []
    for match in matches:
        normalized = match.replace('-', '/')
        normalized_list.append(normalized)
    
    normalized = ', '.join(normalized_list)
    
    return True, normalized, None


def validate_registry_number(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate registry number.
    Accepts: alphanumeric + "Book/Vol" style
    Must not be a sentence; length cap 40
    Returns: (is_valid, normalized_value, warning_reason_if_weak)
    """
    s = normalize_whitespace(s)
    
    # Hard reject: too long
    if len(s) > 40:
        return False, None, f"Registry number too long ({len(s)} > 40 chars)"
    
    # Hard reject: contains sentence punctuation
    if re.search(r'[.,;:!?]', s):
        return False, None, "Contains sentence punctuation (likely narrative)"
    
    # Hard reject: looks like a sentence (multiple words with common stopwords)
    stopwords = ['the', 'is', 'are', 'was', 'were', 'this', 'that', 'with', 'from', 'for']
    tokens = s.lower().split()
    if len(tokens) > 3 and any(sw in tokens for sw in stopwords):
        return False, None, "Contains stopwords (likely narrative sentence)"
    
    # Accept alphanumeric + common separators
    if not re.match(r'^[A-Za-z0-9/\- ]+$', s):
        return False, None, "Contains invalid characters (only alphanumeric, /, -, space allowed)"
    
    # Normalize: uppercase, remove extra spaces
    normalized = re.sub(r'\s+', ' ', s).strip().upper()
    
    return True, normalized, None


def validate_estamp(s: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate e-stamp ID/number.
    Accepts: "e-Stamp No", "eStamp", "PSID", "Challan"
    Extracts identifier token; cap length 50
    Returns: (is_valid, normalized_value, warning_reason_if_weak)
    """
    s = normalize_whitespace(s)
    
    # Remove common prefixes
    s = re.sub(r'^(e[-\s]?stamp|estamp|stamp\s*paper|psid|challan)\s*(?:id|no\.?|number)?\s*[:]?\s*', '', s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Hard reject: too long
    if len(s) > 50:
        return False, None, f"E-stamp ID too long ({len(s)} > 50 chars)"
    
    # Hard reject: empty after prefix removal
    if not s:
        return False, None, "No identifier found after prefix removal"
    
    # Accept alphanumeric + common separators
    if not re.match(r'^[A-Za-z0-9\-_]+$', s):
        return False, None, "Contains invalid characters (only alphanumeric, -, _ allowed)"
    
    # Normalize: uppercase
    normalized = s.upper()
    
    return True, normalized, None


def generic_sentence_rejector(s: str) -> bool:
    """
    Generic check: returns False if looks like narrative sentence.
    Used as fallback for fields without specific validators.
    """
    s = normalize_whitespace(s)
    
    # Reject if too long
    if len(s) > 100:
        return False
    
    # Reject if contains >7 tokens and common stop-phrases
    tokens = s.split()
    if len(tokens) > 7:
        stop_phrases = ['the', 'is', 'are', 'was', 'were', 'this', 'that', 'with', 'from', 'for', 'in', 'on', 'at']
        if any(phrase in s.lower() for phrase in stop_phrases):
            return False
    
    # Reject if contains sentence punctuation
    if re.search(r'[.,;:!?]', s):
        return False
    
    return True


def get_field_validator(field_key: str):
    """
    Get appropriate validator for a field key.
    Returns: validator function or None
    """
    if 'name' in field_key.lower():
        return is_probably_name_line
    elif 'cnic' in field_key.lower() or 'nic' in field_key.lower():
        return validate_cnic
    elif 'plot' in field_key.lower():
        return validate_plot
    elif 'khasra' in field_key.lower():
        return validate_khasra_list
    elif 'registry' in field_key.lower() and 'number' in field_key.lower():
        return validate_registry_number
    elif 'estamp' in field_key.lower() or 'stamp' in field_key.lower():
        return validate_estamp
    
    return None


def test_plausibility_assertions() -> None:
    """
    Unit-style smoke test function to assert mojibake rejection and valid Urdu acceptance.
    
    Tests:
    - "┌⌐╪º╪┤┘ü ╪▓╪º╪¿╪»" is rejected with corrupted/mojibake reason
    - "کاشف زابد" is accepted for buyer/seller
    """
    # Test 1: Mojibake string must be rejected
    mojibake_test = "┌⌐╪º╪┤┘ü ╪▓╪º╪¿╪»"
    is_valid_buyer, reason_buyer = is_plausible_party_name(mojibake_test, role="buyer")
    is_valid_seller, reason_seller = is_plausible_party_name(mojibake_test, role="seller")
    
    assert not is_valid_buyer, f"Mojibake string should be rejected for buyer, but was accepted. Reason: {reason_buyer}"
    assert not is_valid_seller, f"Mojibake string should be rejected for seller, but was accepted. Reason: {reason_seller}"
    assert "corrupted" in reason_buyer.lower() or "mojibake" in reason_buyer.lower(), \
        f"Mojibake rejection reason should contain 'corrupted' or 'mojibake', got: {reason_buyer}"
    
    # Test 2: Valid Urdu name should be accepted
    urdu_name_test = "کاشف زابد"
    is_valid_buyer_urdu, reason_buyer_urdu = is_plausible_party_name(urdu_name_test, role="buyer")
    is_valid_seller_urdu, reason_seller_urdu = is_plausible_party_name(urdu_name_test, role="seller")
    
    assert is_valid_buyer_urdu, f"Valid Urdu name should be accepted for buyer, but was rejected. Reason: {reason_buyer_urdu}"
    assert is_valid_seller_urdu, f"Valid Urdu name should be accepted for seller, but was rejected. Reason: {reason_seller_urdu}"
    
    # Test 3: Additional mojibake examples
    mojibake_examples = [
        "┌⌐╪º╪┤┘ü",
        "╪▓╪º╪¿╪»",
        "┌┐┘│├┤",
        "╪º╪¿╪»",
    ]
    for mojibake_example in mojibake_examples:
        is_valid, reason = is_plausible_party_name(mojibake_example, role="buyer")
        assert not is_valid, f"Mojibake example '{mojibake_example}' should be rejected, but was accepted. Reason: {reason}"
        assert "corrupted" in reason.lower() or "mojibake" in reason.lower(), \
            f"Mojibake rejection reason should contain 'corrupted' or 'mojibake', got: {reason}"
    
    print("test_plausibility_assertions: All tests passed ✓")


if __name__ == "__main__":
    # Run smoke test if executed directly
    test_plausibility_assertions()

