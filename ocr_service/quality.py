from dataclasses import dataclass


@dataclass
class PageQuality:
    quality_score: float
    quality_level: str
    warning_reason: str | None
    avg_chars_per_word: float
    word_count: int


def score_page(text: str, word_boxes: list) -> PageQuality:
    words = [word for word in (text or "").split() if word.strip()]
    word_count = len(words)
    avg_chars_per_word = (
        sum(len(word) for word in words) / word_count if word_count else 0.0
    )

    if word_count < 5:
        return PageQuality(
            quality_score=0.1,
            quality_level="unusable",
            warning_reason=f"Too few detected words ({word_count} < 5)",
            avg_chars_per_word=avg_chars_per_word,
            word_count=word_count,
        )

    box_confidences = [
        float(box.confidence)
        for box in word_boxes
        if getattr(box, "confidence", None) is not None
    ]
    mean_box_confidence = (
        sum(box_confidences) / len(box_confidences) if box_confidences else 0.5
    )

    word_count_score = min(word_count / 40.0, 1.0)
    avg_chars_score = min(avg_chars_per_word / 5.0, 1.0)
    quality_score = max(
        0.0,
        min(1.0, (word_count_score * 0.45) + (avg_chars_score * 0.35) + (mean_box_confidence * 0.20)),
    )

    if avg_chars_per_word < 2.5:
        return PageQuality(
            quality_score=min(quality_score, 0.29),
            quality_level="poor",
            warning_reason=f"Average characters per word too low ({avg_chars_per_word:.2f} < 2.50)",
            avg_chars_per_word=avg_chars_per_word,
            word_count=word_count,
        )

    if quality_score < 0.3:
        return PageQuality(
            quality_score=quality_score,
            quality_level="poor",
            warning_reason=f"Quality score too low ({quality_score:.2f} < 0.30)",
            avg_chars_per_word=avg_chars_per_word,
            word_count=word_count,
        )

    if quality_score >= 0.7:
        quality_level = "good"
        warning_reason = None
    elif quality_score >= 0.45:
        quality_level = "fair"
        warning_reason = None
    else:
        quality_level = "poor"
        warning_reason = "Weak OCR text structure after preprocessing"

    return PageQuality(
        quality_score=quality_score,
        quality_level=quality_level,
        warning_reason=warning_reason,
        avg_chars_per_word=avg_chars_per_word,
        word_count=word_count,
    )
