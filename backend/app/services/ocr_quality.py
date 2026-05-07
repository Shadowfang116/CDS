def compute_ocr_quality_signal(text: str, avg_confidence: float | None, settings) -> str:
    char_count = len(text.strip())
    if char_count < settings.OCR_LOW_CHAR_COUNT_THRESHOLD:
        return "LOW_CONFIDENCE"
    if avg_confidence is not None and avg_confidence < settings.OCR_LOW_AVG_CONFIDENCE_THRESHOLD:
        return "LOW_CONFIDENCE"
    non_alpha = sum(1 for c in text if not c.isalnum() and not c.isspace())
    ratio = non_alpha / max(len(text), 1)
    if ratio > settings.OCR_HIGH_NOISE_RATIO_THRESHOLD:
        return "REVIEW_REQUIRED"
    return "GOOD"