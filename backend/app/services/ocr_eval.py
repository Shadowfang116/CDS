"""DEV-ONLY OCR evaluation metrics used by scripts/dev/eval_*.py. Not on the production path."""
import logging
import re
import unicodedata
from typing import Dict, Any, Optional

from app.services.ocr_text import normalize_unicode

# Digit normalization mapping (reuse from ocr_text.py)
URDU_DIGIT_MAP = {
    '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4',
    '\u0665': '5', '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9',
    '\u06F0': '0', '\u06F1': '1', '\u06F2': '2', '\u06F3': '3', '\u06F4': '4',
    '\u06F5': '5', '\u06F6': '6', '\u06F7': '7', '\u06F8': '8', '\u06F9': '9',
}


def normalize_digits(text:
    str) -> str:
    """Normalize Urdu/Arabic-Indic digits to ASCII."""
    if not text:
        return ""
    return ''.join(URDU_DIGIT_MAP.get(c, c) for c in text)

logger = logging.getLogger(__name__)


def urdu_char_ratio(text: str) -> float:
    return sum(1 for char in text if "\u0600" <= char <= "\u06ff") / max(len(text), 1)


def latin_ratio(text: str) -> float:
    return sum(1 for char in text if char.isascii() and char.isalpha()) / max(len(text), 1)


def garbage_ratio(text: str) -> float:
    garbage = sum(
        1
        for char in text
        if not char.isspace() and unicodedata.category(char)[0] in {"C", "S"}
    )
    return garbage / max(len(text), 1)


def whitespace_ratio(text: str) -> float:
    return sum(1 for char in text if char.isspace()) / max(len(text), 1)


def normalize_for_eval(text:
    str) -> str:
    """
    Normalize text for evaluation comparison.
    
    Applies:
    - Unicode NFKC normalization
    - Digit normalization (Urdu digits -> ASCII)
    - Strip extra whitespace
    - Remove non-informative punctuation repeats
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Unicode NFKC normalization
    text = normalize_unicode(text)
    
    # Digit normalization (Urdu digits -> ASCII)
    text = normalize_digits(text)
    
    # Strip extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove excessive punctuation repeats (e.g., "..." -> ".")
    text = re.sub(r'\.{3,}', '.', text)
    text = re.sub(r',{2,}', ',', text)
    text = re.sub(r'-{3,}', '-', text)
    
    return text


def edit_distance(s1:
    str, s2: str) -> int:
    """
    Compute Levenshtein edit distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        Edit distance (minimum number of insertions, deletions, substitutions)
    """
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    
    # Create matrix
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # Initialize base cases
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    # Fill matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + 1     # substitution
                )
    
    return dp[m][n]


def char_error_rate(pred:
    str, gt: str) -> float:
    """
    Compute Character Error Rate (CER).
    
    CER = edit_distance(pred, gt) / max(1, len(gt))
    
    Args:
        pred: Predicted text
        gt: Ground truth text
    
    Returns:
        CER (0.0 = perfect, higher = worse)
    """
    if not gt:
        return 1.0 if pred else 0.0
    
    dist = edit_distance(pred, gt)
    return dist / max(1, len(gt))


def word_error_rate(pred:
    str, gt: str) -> float:
    """
    Compute Word Error Rate (WER) using whitespace tokenization.
    
    WER = edit_distance(words_pred, words_gt) / max(1, len(words_gt))
    
    Args:
        pred: Predicted text
        gt: Ground truth text
    
    Returns:
        WER (0.0 = perfect, higher = worse)
    """
    pred_words = pred.split()
    gt_words = gt.split()
    
    if not gt_words:
        return 1.0 if pred_words else 0.0
    
    dp = list(range(len(gt_words) + 1))
    for i, pred_word in enumerate(pred_words, start=1):
        previous = dp[0]
        dp[0] = i
        for j, gt_word in enumerate(gt_words, start=1):
            current = dp[j]
            dp[j] = min(
                dp[j] + 1,
                dp[j - 1] + 1,
                previous + (pred_word != gt_word),
            )
            previous = current
    return dp[-1] / max(1, len(gt_words))


def overlap_f1(pred:
    str, gt: str) -> float:
    """
    Compute token set F1 score after normalization.
    
    Good for partial ground truth (key lines only).
    
    Args:
        pred: Predicted text
        gt: Ground truth text
    
    Returns:
        F1 score (0.0 = no overlap, 1.0 = perfect match)
    """
    # Normalize both texts
    pred_norm = normalize_for_eval(pred)
    gt_norm = normalize_for_eval(gt)
    
    # Tokenize into words
    pred_tokens = set(pred_norm.split())
    gt_tokens = set(gt_norm.split())
    
    if not gt_tokens:
        return 1.0 if not pred_tokens else 0.0
    
    # Compute intersection and union
    intersection = pred_tokens & gt_tokens
    union = pred_tokens | gt_tokens
    
    if not union:
        return 1.0
    
    # F1 = 2 * (precision * recall) / (precision + recall)
    # precision = |intersection| / |pred_tokens|
    # recall = |intersection| / |gt_tokens|
    precision = len(intersection) / max(1, len(pred_tokens))
    recall = len(intersection) / max(1, len(gt_tokens))
    
    if precision + recall == 0:
        return 0.0
    
    f1 = 2 * (precision * recall) / (precision + recall)
    return f1


def evaluate_ocr_result(
    pred_text: str,
    gt_text: Optional[str] = None,
    compute_cer_wer: bool = True
) -> Dict[str, Any]:
    """
    Evaluate OCR result against ground truth (if available).
    
    Always computes quality metrics (ratios, garbage).
    Optionally computes CER/WER/F1 if GT is provided.
    
    Args:
        pred_text: Predicted OCR text
        gt_text: Optional ground truth text
        compute_cer_wer: Whether to compute CER/WER/F1 (requires GT)
    
    Returns:
        Dict with metrics:
        {
            "cer": ... (if GT provided),
            "wer": ... (if GT provided),
            "f1": ... (if GT provided),
            "len_pred": ...,
            "len_gt": ... (if GT provided),
            "urdu_ratio": ...,
            "latin_ratio": ...,
            "garbage_ratio": ...,
            "whitespace_ratio": ...,
        }
    """
    result: Dict[str, Any] = {
        "len_pred": len(pred_text) if pred_text else 0,
        "urdu_ratio": urdu_char_ratio(pred_text) if pred_text else 0.0,
        "latin_ratio": latin_ratio(pred_text) if pred_text else 0.0,
        "garbage_ratio": garbage_ratio(pred_text) if pred_text else 0.0,
        "whitespace_ratio": whitespace_ratio(pred_text) if pred_text else 0.0,
    }
    
    if gt_text is not None:
        result["len_gt"] = len(gt_text)
        
        if compute_cer_wer and gt_text:
            # Normalize both texts for comparison
            pred_norm = normalize_for_eval(pred_text)
            gt_norm = normalize_for_eval(gt_text)
            
            result["cer"] = char_error_rate(pred_norm, gt_norm)
            result["wer"] = word_error_rate(pred_norm, gt_norm)
            result["f1"] = overlap_f1(pred_norm, gt_norm)
    
    return result


def normalize_field_value(value: Any, normalization: str = "text") -> str:
    """Normalize an extracted legal field without applying semantic correction."""
    text = normalize_digits(str(value or ""))
    text = unicodedata.normalize("NFKC", text).strip().lower()
    if normalization in {"amount", "identifier"}:
        text = re.sub(r"[\s,٬،/\\-]", "", text)
        if normalization == "amount":
            text = re.sub(r"[^0-9]", "", text)
    elif normalization == "area":
        text = re.sub(r"\s+", " ", text)
    else:
        text = re.sub(r"\s+", " ", text)
    return text


def evaluate_field_predictions(
    references: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score field extraction and evidence links against page-level references."""
    prediction_map = {
        (row.get("document_id"), int(row.get("page", row.get("source_page", 0))), row.get("field")): row
        for row in predictions
    }
    rows: list[dict[str, Any]] = []
    exact_matches = normalized_matches = false_positives = missing = missing_links = 0
    for reference in references:
        key = (reference.get("document_id"), int(reference.get("page", 0)), reference.get("field"))
        prediction = prediction_map.get(key)
        expected = str(reference.get("reference_value", ""))
        normalization = reference.get("normalization", "text")
        predicted = str(prediction.get("predicted_value", "")) if prediction else ""
        exact = bool(prediction) and predicted.strip() == expected.strip()
        normalized = bool(prediction) and normalize_field_value(predicted, normalization) == normalize_field_value(expected, normalization)
        linked = bool(prediction and prediction.get("source_page") and prediction.get("snippet"))
        if exact:
            exact_matches += 1
        if normalized:
            normalized_matches += 1
        elif prediction:
            false_positives += 1
        else:
            missing += 1
        if prediction and not linked:
            missing_links += 1
        rows.append({
            "document_id": reference.get("document_id"),
            "page": reference.get("page"),
            "field": reference.get("field"),
            "exact_match": exact,
            "normalized_match": normalized,
            "missing": not bool(prediction),
            "false_positive": bool(prediction) and not normalized,
            "evidence_linked": linked,
            "confidence": prediction.get("confidence") if prediction else None,
        })
    total = len(references)
    return {
        "fields_total": total,
        "exact_matches": exact_matches,
        "normalized_matches": normalized_matches,
        "false_positives": false_positives,
        "missing_values": missing,
        "missing_evidence_links": missing_links,
        "exact_match_rate": exact_matches / max(1, total),
        "normalized_match_rate": normalized_matches / max(1, total),
        "rows": rows,
    }
