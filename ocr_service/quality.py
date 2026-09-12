from dataclasses import dataclass
import unicodedata


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
    confidence_known = bool(box_confidences)
    mean_box_confidence = sum(box_confidences) / len(box_confidences) if confidence_known else 0.0

    # Text amount is a weak signal: a short, valid Urdu page should not be
    # marked poor simply because it has fewer words than a full deed.
    word_count_score = min(word_count / 8.0, 1.0)
    avg_chars_score = min(avg_chars_per_word / 3.5, 1.0)
    script_score = _script_consistency(text)
    garbage_score = 1.0 - min(_garbage_ratio(text) * 5.0, 1.0)
    quality_score = max(
        0.0,
        min(
            1.0,
            (word_count_score * 0.25)
            + (avg_chars_score * 0.20)
            + (mean_box_confidence * 0.35)
            + (script_score * 0.10)
            + (garbage_score * 0.10),
        ),
    )

    if not confidence_known:
        quality_score = min(quality_score, 0.49)

    if avg_chars_per_word < 2.5:
        return PageQuality(
            quality_score=min(quality_score, 0.29),
            quality_level="poor",
            warning_reason=f"Average characters per word too low ({avg_chars_per_word:.2f} < 2.50)",
            avg_chars_per_word=avg_chars_per_word,
            word_count=word_count,
        )

    if _garbage_ratio(text) > 0.08:
        return PageQuality(
            quality_score=min(quality_score, 0.29),
            quality_level="poor",
            warning_reason="Too many garbage or replacement characters",
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
        warning_reason = None if confidence_known else "OCR confidence unavailable"
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


def _script_consistency(text: str) -> float:
    informative = [char for char in text if not char.isspace() and not unicodedata.category(char).startswith("P")]
    if not informative:
        return 0.0
    supported = sum(
        1
        for char in informative
        if ("\u0600" <= char <= "\u06ff") or (char.isascii() and (char.isalnum() or char in "./-"))
    )
    return supported / len(informative)


def _garbage_ratio(text: str) -> float:
    if not text:
        return 0.0
    garbage = sum(
        1
        for char in text
        if char == "�" or unicodedata.category(char) in {"Cc", "Cf", "Co", "Cn"}
    )
    return garbage / max(1, len(text))
