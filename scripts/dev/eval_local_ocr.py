#!/usr/bin/env python3
"""Run a local Tesseract/PaddleOCR comparison against benchmark pages."""
import argparse
import json
import sys
import time
from pathlib import Path

import fitz
import numpy as np

OCR_ROOT = Path(__file__).resolve().parents[2] / "ocr_service"
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(OCR_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from engines.paddleocr_engine import run_paddleocr  # noqa: E402
from engines.tesseract_engine import run_tesseract  # noqa: E402
from app.services.ocr_eval import edit_distance, evaluate_ocr_result, normalize_for_eval  # noqa: E402


def _resolve_path(value: str, manifest_path: Path, data_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = data_root / path
    if candidate.exists():
        return candidate
    return manifest_path.parent.parent / path


def _load_pages(manifest_path: Path, data_root: Path, require_verified: bool = True) -> list[dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing: list[str] = []
    pages: list[dict] = []
    for item in manifest.get("items", []):
        pdf_value = item.get("source_pdf") or item.get("pdf_path") or item.get("filename")
        if not pdf_value:
            missing.append(f"{item.get('id', '<unknown>')}: source_pdf")
            continue
        pdf_path = _resolve_path(pdf_value, manifest_path, data_root)
        for page in item.get("pages", []):
            gt_value = page.get("ground_truth_path") or page.get("gt_path")
            page_number = int(page.get("page", page.get("page_index", 0)))
            page_index = page_number if "page_index" in page else max(0, page_number - 1)
            if not pdf_path.exists():
                missing.append(str(pdf_path))
            if not gt_value:
                missing.append(f"{item.get('id', '<unknown>')} page {page_number}: ground_truth_path")
                continue
            gt_path = _resolve_path(gt_value, manifest_path, data_root)
            if not gt_path.exists():
                missing.append(str(gt_path))
            if require_verified and page.get("human_verified") is not True:
                raise ValueError(
                    f"Page {item.get('id', '<unknown>')}:{page_number} lacks human-verified ground truth"
                )
            if pdf_path.exists() and gt_path.exists():
                pages.append(
                    {
                        "doc_id": item["id"],
                        "pdf_path": pdf_path,
                        "page_index": page_index,
                        "gt_path": gt_path,
                        "document_class": item.get("document_class"),
                        "rulebook_targets": item.get("rulebook_targets", []),
                        "human_verified": page.get("human_verified", False),
                    }
                )
    if missing:
        raise FileNotFoundError("Benchmark is incomplete; missing: " + ", ".join(sorted(set(missing))))
    if not pages:
        raise ValueError("Benchmark contains no evaluated pages")
    return pages


def _render_page(pdf_path: Path, page_index: int, dpi: int) -> np.ndarray:
    document = fitz.open(pdf_path)
    try:
        page = document[page_index]
        scale = dpi / 72.0
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    finally:
        document.close()


def _rss_bytes() -> int | None:
    try:
        import psutil
        return psutil.Process().memory_info().rss
    except ImportError:
        return None


def _word_edit_distance(prediction: str, reference: str) -> int:
    predicted = prediction.split()
    expected = reference.split()
    dp = list(range(len(expected) + 1))
    for i, word in enumerate(predicted, start=1):
        previous = dp[0]
        dp[0] = i
        for j, expected_word in enumerate(expected, start=1):
            current = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, previous + (word != expected_word))
            previous = current
    return dp[-1]


def _summarize_results(rows: list[dict]) -> dict:
    if not rows:
        return {"pages": 0}
    reference_chars = sum(row["reference_chars"] for row in rows)
    edit_total = sum(row["edit_distance"] for row in rows)
    reference_words = sum(row["reference_words"] for row in rows)
    word_edit_total = sum(row["word_edit_distance"] for row in rows)
    return {
        "pages": len(rows),
        "aggregate_cer": edit_total / max(1, reference_chars),
        "character_accuracy": max(0.0, 1.0 - edit_total / max(1, reference_chars)),
        "aggregate_wer": word_edit_total / max(1, reference_words),
        "avg_f1": sum(row["f1"] for row in rows) / len(rows),
        "avg_confidence": sum(row["confidence"] or 0.0 for row in rows) / len(rows),
        "avg_elapsed_seconds": sum(row["elapsed_seconds"] for row in rows) / len(rows),
    }


def evaluate(
    manifest_path: Path,
    data_root: Path,
    output_path: Path,
    engines: tuple[str, ...],
    dpi: int,
    require_verified: bool = True,
) -> dict:
    pages = _load_pages(manifest_path, data_root, require_verified=require_verified)
    runners = {"tesseract": run_tesseract, "paddleocr": run_paddleocr}
    results: dict[str, list[dict]] = {engine: [] for engine in engines}
    raw_root = output_path.parent / "raw"
    for page in pages:
        image = _render_page(page["pdf_path"], page["page_index"], dpi)
        ground_truth = page["gt_path"].read_text(encoding="utf-8").strip()
        normalized_ground_truth = normalize_for_eval(ground_truth)
        for engine_name in engines:
            before = _rss_bytes()
            started = time.perf_counter()
            result = runners[engine_name](image)
            elapsed = time.perf_counter() - started
            after = _rss_bytes()
            normalized_prediction = normalize_for_eval(result.text)
            metrics = evaluate_ocr_result(result.text, ground_truth)
            raw_path = raw_root / engine_name / f"{page['doc_id']}.page{page['page_index'] + 1}.txt"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(result.text, encoding="utf-8")
            results[engine_name].append(
                {
                    "doc_id": page["doc_id"],
                    "document_class": page["document_class"],
                    "rulebook_targets": page["rulebook_targets"],
                    "page_num": page["page_index"] + 1,
                    "requested_engine": engine_name,
                    "actual_engine": result.engine_used,
                    "human_verified": page["human_verified"],
                    "cer": metrics["cer"],
                    "wer": metrics["wer"],
                    "f1": metrics["f1"],
                    "edit_distance": edit_distance(normalized_prediction, normalized_ground_truth),
                    "word_edit_distance": _word_edit_distance(normalized_prediction, normalized_ground_truth),
                    "reference_chars": len(normalized_ground_truth),
                    "reference_words": len(normalized_ground_truth.split()),
                    "confidence": result.confidence,
                    "quality_score": result.quality_score,
                    "quality_level": result.quality_level,
                    "text_chars": len(result.text),
                    "elapsed_seconds": round(elapsed, 3),
                    "rss_delta_bytes": after - before if before is not None and after is not None else None,
                    "raw_ocr_text": str(raw_path),
                    "warning": result.warning_reason,
                }
            )

    report = {
        "benchmark_status": "DRAFT_REFERENCE_ONLY" if not require_verified else "HUMAN_VERIFIED",
        "accuracy_status": "NOT_RELEASE_ACCURACY" if not require_verified else "RELEASE_CANDIDATE_METRICS",
        "manifest": str(manifest_path),
        "benchmark_pages": len(pages),
        "dpi": dpi,
        "engines": {},
    }
    for engine_name, rows in results.items():
        report["engines"][engine_name] = {**_summarize_results(rows), "page_results": rows}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate local OCR engines against reviewed ground truth")
    parser.add_argument("--manifest", type=Path, default=Path("datasets/urdu_ocr/manifests/manifest.json"))
    parser.add_argument("--data-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("datasets/urdu_ocr/reports/local_comparison.json"))
    parser.add_argument("--engine", choices=("tesseract", "paddleocr", "both"), default="both")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()
    engines = ("tesseract", "paddleocr") if args.engine == "both" else (args.engine,)
    try:
        summary = evaluate(
            args.manifest,
            args.data_root,
            args.out,
            engines,
            max(72, args.dpi),
            require_verified=not args.allow_unverified,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"BENCHMARK BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
