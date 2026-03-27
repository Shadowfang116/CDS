"""Phase 9: OCR evaluation metrics for Urdu OCR regression testing."""
import logging
import re
from typing import Dict, Any, Optional

from app.services.ocr_quality import (
    urdu_char_ratio,
    latin_ratio,
    garbage_ratio,
    whitespace_ratio,
)
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
    # Tokenize by whitespace
    pred_words = pred.split()
    gt_words = gt.split()
    
    if not gt_words:
        return 1.0 if pred_words else 0.0
    
    dist = edit_distance(' '.join(pred_words), ' '.join(gt_words))
    # Approximate WER using character-level edit distance on word sequences
    # More accurate would be word-level edit distance, but this is simpler
    return dist / max(1, len(' '.join(gt_words)))


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

