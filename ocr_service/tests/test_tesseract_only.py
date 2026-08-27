import sys
from pathlib import Path


OCR_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OCR_SERVICE_ROOT))

from main import REQUESTED_DEFAULT_ENGINE, _normalize_engine_name, _resolve_engine_name  # noqa: E402
from schemas import OcrRequest  # noqa: E402


def test_ocr_service_uses_tesseract_for_default_and_legacy_requests():
    assert REQUESTED_DEFAULT_ENGINE == "tesseract"
    assert _normalize_engine_name(None) == "tesseract"
    assert _normalize_engine_name("surya") == "tesseract"
    assert _resolve_engine_name("surya") == "tesseract"
    assert OcrRequest(document_id="doc", pages=["image"], engine="tesseract").engine == "tesseract"
