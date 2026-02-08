"""Name-line extractor for party name fields - filters narrative sentences."""
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


# Stopwords (bank-safe, Pakistan doc-friendly)
STOPWORDS = {
    "appears", "lawful", "owner", "property", "competent", "sell", "vide", "reference",
    "letter", "regard", "hereby", "whereas", "submitted", "observed", "plot", "khasra",
    "mouza", "tehsil", "district", "lda", "dha", "rda", "in", "of", "the", "and", "to",
    "for", "with", "through", "under", "above", "mentioned", "shall", "will", "may",
    "has", "have", "had", "is", "are", "was", "were", "been", "being", "be", "do", "does",
    "did", "done", "can", "could", "should", "would", "must", "might", "this", "that",
    "these", "those", "a", "an", "as", "at", "by", "from", "into", "on", "onto", "per",
    "than", "up", "via", "within", "without",
}

# Sentence-verb indicators
SENTENCE_VERBS = {
    "appears", "undertakes", "declares", "states", "confirms", "certifies", "submits",
    "requests", "authorizes", "agrees", "shall", "will", "may", "has", "have", "had",
    "is", "are", "was", "were", "been", "being", "be", "do", "does", "did", "done",
    "can", "could", "should", "would", "must", "might", "acknowledges", "warrants",
    "represents", "covenants", "undertakes", "agrees", "warrants", "represents",
}


@dataclass
class NameLineResult:
    """Accepted name line with metadata."""
    value: str
    snippet: str
    score: float
    flags: List[str]  # e.g., ["has_initial", "short_tokens"]


@dataclass
class RejectedLine:
    """Rejected line with reason."""
    line: str
    reason_flags: List[str]  # e.g., ["too_long", "has_digits", "has_stopword"]


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for deduplication."""
    return re.sub(r'\s+', ' ', text.strip())


def extract_name_lines(ocr_text: str) -> Tuple[List[NameLineResult], List[RejectedLine]]:
    """
    Extract name-like lines from OCR text.
    
    Returns:
        (accepted_lines, rejected_lines)
    """
    accepted = []
    rejected = []
    
    # Split into lines
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    
    for line in lines:
        original_line = line
        line_lower = line.lower()
        
        # Hard filters (reject immediately)
        rejection_flags = []
        
        # 1. Length check
        if len(line) > 60:
            rejection_flags.append("too_long")
        
        # 2. Contains digits
        if re.search(r'\d', line):
            rejection_flags.append("has_digits")
        
        # 3. Contains sentence punctuation (except allowed in names)
        if re.search(r'[;:]', line):
            rejection_flags.append("has_sentence_punct")
        # Allow commas only if they appear in patterns like "Name, Son of" (but this is risky)
        # For now, reject lines with commas unless they're clearly name patterns
        if ',' in line and not re.search(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*(?:son|s/o|d/o|w/o)', line, re.IGNORECASE):
            rejection_flags.append("has_comma")
        
        # 4. Token count check
        tokens = line.split()
        token_count = len(tokens)
        if token_count < 2 or token_count > 5:
            rejection_flags.append("bad_token_count")
        
        # 5. Stopword check
        has_stopword = False
        for token in tokens:
            if token.lower() in STOPWORDS:
                has_stopword = True
                rejection_flags.append("has_stopword")
                break
        
        # 6. Sentence verb check
        has_verb = False
        for token in tokens:
            if token.lower() in SENTENCE_VERBS:
                has_verb = True
                rejection_flags.append("has_sentence_verb")
                break
        
        # 7. Alphabetic ratio check
        alpha_chars = sum(1 for c in line if c.isalpha() or c.isspace())
        alpha_ratio = alpha_chars / len(line) if line else 0
        if alpha_ratio < 0.85:
            rejection_flags.append("low_alpha_ratio")
        
        # If any hard filter fails, reject
        if rejection_flags:
            rejected.append(RejectedLine(line=original_line, reason_flags=rejection_flags))
            continue
        
        # Soft scoring (accept if score >= 0.75)
        score = 1.0
        quality_flags = []
        
        # Penalize single-char tokens (initials like "M." are okay, but too many is bad)
        single_char_tokens = sum(1 for t in tokens if len(t) == 1)
        if single_char_tokens > 1:
            score -= 0.1 * (single_char_tokens - 1)
            quality_flags.append("many_initials")
        elif single_char_tokens == 1:
            quality_flags.append("has_initial")
        
        # Penalize very short tokens (< 3 chars, excluding initials)
        short_tokens = sum(1 for t in tokens if len(t) < 3 and len(t) > 1)
        if short_tokens > 3:
            score -= 0.15
            quality_flags.append("many_short_tokens")
        elif short_tokens > 0:
            quality_flags.append("has_short_tokens")
        
        # Bonus for proper capitalization (Title Case or ALL CAPS)
        if all(t[0].isupper() for t in tokens if t):
            score += 0.05
            quality_flags.append("proper_case")
        
        # Accept if score >= 0.75
        if score >= 0.75:
            accepted.append(NameLineResult(
                value=line.strip(),
                snippet=original_line,
                score=score,
                flags=quality_flags,
            ))
        else:
            rejected.append(RejectedLine(
                line=original_line,
                reason_flags=["low_score"] + quality_flags,
            ))
    
    return accepted, rejected


def is_name_like_field(field_key: str) -> bool:
    """Check if a field key is name-like and should use name-line filtering."""
    name_patterns = [
        "party.name",
        "seller.name",
        "buyer.name",
        "representative.name",
        "borrower.name",
        "applicant.name",
    ]
    return any(pattern in field_key.lower() for pattern in name_patterns)

