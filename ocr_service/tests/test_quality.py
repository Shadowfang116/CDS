import sys
from pathlib import Path


OCR_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OCR_SERVICE_ROOT))

from quality import score_page  # noqa: E402
from schemas import WordBox  # noqa: E402


def test_score_page_does_not_penalize_valid_sparse_text_by_word_count() -> None:
    text = "یہ ایک مختصر مگر درست اردو متن ہے"
    boxes = [WordBox(text=word, confidence=0.95) for word in text.split()]

    result = score_page(text, boxes)

    assert result.quality_level == "good"
    assert result.quality_score >= 0.75


def test_score_page_without_confidence_is_not_treated_as_half_confident() -> None:
    text = "یہ ایک درست اردو متن ہے"
    boxes = [WordBox(text=word) for word in text.split()]

    result = score_page(text, boxes)

    assert result.quality_score < 0.5


def test_score_page_accepts_mixed_urdu_english_with_known_confidence() -> None:
    text = "مالک Owner رقبہ Area 12 کنال Lahore"
    boxes = [WordBox(text=word, confidence=0.92) for word in text.split()]

    result = score_page(text, boxes)

    assert result.quality_level == "good"
    assert result.quality_score >= 0.8


def test_score_page_downgrades_replacement_character_garbage() -> None:
    text = "مالک � � � رقبہ Area 12 کنال"
    boxes = [WordBox(text=word, confidence=0.95) for word in text.split()]

    result = score_page(text, boxes)

    assert result.quality_level == "poor"
    assert result.warning_reason == "Too many garbage or replacement characters"


def test_score_page_marks_blank_page_unusable() -> None:
    result = score_page("", [])

    assert result.quality_level == "unusable"
    assert result.quality_score == 0.1
