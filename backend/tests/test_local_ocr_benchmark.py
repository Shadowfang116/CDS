import json
from pathlib import Path

import pytest

from scripts.dev.eval_local_ocr import _load_pages, _summarize_results


def test_load_pages_resolves_external_absolute_paths_and_requires_review(tmp_path: Path):
    pdf = tmp_path / "page.pdf"
    gt = tmp_path / "page.txt"
    pdf.write_bytes(b"pdf")
    gt.write_text("verified", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "doc-1",
                        "source_pdf": str(pdf),
                        "pages": [
                            {
                                "page": 1,
                                "ground_truth_path": str(gt),
                                "human_verified": True,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    pages = _load_pages(manifest, tmp_path, require_verified=True)

    assert pages[0]["pdf_path"] == pdf
    assert pages[0]["gt_path"] == gt
    assert pages[0]["page_index"] == 0


def test_load_pages_rejects_unverified_transcription(tmp_path: Path):
    pdf = tmp_path / "page.pdf"
    gt = tmp_path / "page.txt"
    pdf.write_bytes(b"pdf")
    gt.write_text("draft", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "doc-1",
                        "source_pdf": str(pdf),
                        "pages": [
                            {
                                "page": 1,
                                "ground_truth_path": str(gt),
                                "human_verified": False,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="human-verified"):
        _load_pages(manifest, tmp_path, require_verified=True)


def test_summary_reports_weighted_totals_and_character_accuracy():
    summary = _summarize_results(
        [
            {
                "cer": 0.1,
                "wer": 0.2,
                "f1": 0.8,
                "reference_chars": 100,
                "edit_distance": 10,
                "reference_words": 20,
                "word_edit_distance": 4,
                "confidence": 0.8,
                "elapsed_seconds": 1.0,
            },
            {
                "cer": 0.5,
                "wer": 0.4,
                "f1": 0.4,
                "reference_chars": 10,
                "edit_distance": 5,
                "reference_words": 5,
                "word_edit_distance": 2,
                "confidence": 0.6,
                "elapsed_seconds": 2.0,
            },
        ]
    )

    assert summary["aggregate_cer"] == pytest.approx(15 / 110)
    assert summary["character_accuracy"] == pytest.approx(1 - 15 / 110)
    assert summary["pages"] == 2
