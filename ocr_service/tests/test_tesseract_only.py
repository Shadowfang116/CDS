import sys
from pathlib import Path

import numpy as np


OCR_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OCR_SERVICE_ROOT))

from main import REQUESTED_DEFAULT_ENGINE, _normalize_engine_name, _resolve_engine_name, _select_engine  # noqa: E402
from engines.paddleocr_engine import _parse_prediction, run_paddleocr  # noqa: E402
from engines.tesseract_engine import run_tesseract  # noqa: E402
from schemas import OcrRequest  # noqa: E402


def test_ocr_service_uses_tesseract_for_default_and_legacy_requests():
    assert REQUESTED_DEFAULT_ENGINE == "tesseract"
    assert _normalize_engine_name(None) == "tesseract"
    assert _normalize_engine_name("surya") == "tesseract"
    assert _resolve_engine_name("surya") == "tesseract"
    assert OcrRequest(document_id="doc", pages=["image"], engine="tesseract").engine == "tesseract"


def test_ocr_service_selects_paddleocr_without_replacing_tesseract():
    assert _normalize_engine_name("paddleocr") == "paddleocr"
    assert _resolve_engine_name("paddleocr") == "paddleocr"
    assert _select_engine("paddleocr") is run_paddleocr
    assert _select_engine("tesseract") is run_tesseract


def test_paddleocr_prediction_is_converted_to_cds_page_shape():
    text, boxes = _parse_prediction(
        {
            "rec_texts": ["مالک", "رقبہ"],
            "rec_scores": [0.91, 0.84],
            "rec_boxes": [[0, 0, 100, 20], [0, 30, 100, 50]],
        }
    )

    assert text == "مالک\nرقبہ"
    assert [box.confidence for box in boxes] == [0.91, 0.84]
    assert boxes[0].bbox == [0.0, 0.0, 100.0, 20.0]


def test_paddleocr_result_includes_recalibrated_quality_score(monkeypatch):
    class FakePaddle:
        def predict(self, image):
            return [{
                "rec_texts": ["مالک", "Owner", "رقبہ", "12", "کنال"],
                "rec_scores": [0.95, 0.95, 0.95, 0.95, 0.95],
                "rec_boxes": [[0, 0, 10, 10]] * 5,
            }]

    monkeypatch.setattr("engines.paddleocr_engine._get_ocr", lambda: FakePaddle())

    result = run_paddleocr(np.zeros((100, 100, 3), dtype=np.uint8))

    assert result.quality_score is not None
    assert result.quality_level in {"good", "fair", "poor"}
