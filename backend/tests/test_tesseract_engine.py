"""Unit tests for single-pass Tesseract OCR engine (F4 fix)."""
import sys
from pathlib import Path

ocr_service_dir = Path(__file__).resolve().parent.parent.parent / "ocr_service"
sys.path.insert(0, str(ocr_service_dir))

from engines.tesseract_engine import reconstruct_text_from_data, _normalize_confidence


def test_reconstruct_text_from_data():
    """Verify single-pass reading order reconstruction across blocks and lines."""
    mock_data = {
        "text": ["Hello", "World", "Second", "Line", "New", "Block"],
        "block_num": [1, 1, 1, 1, 2, 2],
        "par_num": [1, 1, 1, 1, 1, 1],
        "line_num": [1, 1, 2, 2, 1, 1],
    }
    text = reconstruct_text_from_data(mock_data)
    expected = "Hello World\nSecond Line\n\nNew Block"
    assert text == expected


def test_normalize_confidence():
    """Verify confidence values 0-100 and 0.0-1.0 normalization."""
    assert _normalize_confidence(95.0) == 0.95
    assert _normalize_confidence(0.85) == 0.85
    assert _normalize_confidence(-1.0) is None
    assert _normalize_confidence("invalid") is None
