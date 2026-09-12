import inspect
import uuid

from app.services.ocr_pipeline import run_ocr_pipeline
from app.workers.tasks_ocr_rerun import (
    _run_default_page_ocr,
    _uses_shared_ocr_path,
)


def test_ocr_pipeline_defaults_to_paddleocr():
    assert inspect.signature(run_ocr_pipeline).parameters["engine"].default == "paddleocr"


def test_default_page_reruns_use_the_shared_ocr_service():
    assert _uses_shared_ocr_path({}) is True
    assert _uses_shared_ocr_path({"force_profile": "enhanced"}) is False


def test_default_page_ocr_preserves_shared_engine_metadata(monkeypatch):
    class FakePage:
        minio_key_page_pdf = "pages/example.pdf"

    async def fake_run_ocr_pipeline(**kwargs):
        assert kwargs["document_id"] == "00000000-0000-0000-0000-000000000001"
        assert kwargs["page_images"] == ["encoded-page"]
        return type(
            "FakePipelineResult",
            (),
            {
                "pages": [
                    type(
                        "FakePageResult",
                        (),
                        {
                            "text": "متن",
                            "confidence": 0.91,
                            "engine_used": "paddleocr",
                            "quality_score": 0.78,
                            "quality_level": "good",
                        },
                    )()
                ]
            },
        )()

    monkeypatch.setattr(
        "app.workers.tasks_ocr_rerun.render_page_asset_to_base64_png",
        lambda key, content_type: "encoded-page",
    )
    monkeypatch.setattr(
        "app.workers.tasks_ocr_rerun.run_ocr_pipeline", fake_run_ocr_pipeline
    )

    result = _run_default_page_ocr(
        uuid.UUID("00000000-0000-0000-0000-000000000001"), FakePage(), "application/pdf"
    )

    assert result == (
        "متن",
        0.91,
        {"engine_used": "paddleocr", "quality_score": 0.78, "quality_level": "good"},
    )
