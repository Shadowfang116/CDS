import inspect

from app.services.ocr_pipeline import run_ocr_pipeline


def test_ocr_pipeline_defaults_to_paddleocr():
    assert inspect.signature(run_ocr_pipeline).parameters["engine"].default == "paddleocr"
