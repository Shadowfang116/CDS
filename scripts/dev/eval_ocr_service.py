#!/usr/bin/env python3
"""Microservice-level OCR evaluation runner that tests POST /ocr directly."""
import argparse
import base64
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add backend to path for ocr_eval metrics
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.ocr_eval import evaluate_ocr_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def evaluate_ocr_service(
    service_url: str,
    manifest_path: Path,
    samples_dir: Path,
    output_dir: Path,
    engine: str = "tesseract",
) -> Dict[str, Any]:
    """Evaluates the running ocr_service microservice against golden samples."""
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    results = []
    missing_files = []
    total_cer, total_wer, total_f1 = 0.0, 0.0, 0.0
    evaluated_pages = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    for item in manifest.get("items", []):
        doc_id = item["id"]
        pdf_name = item.get("filename", f"{doc_id}.pdf")
        pages_gt = item.get("ground_truth_pages") or [page.get("gt_path") for page in item.get("pages", [])]

        pages_payload = []
        for p_idx, gt_rel in enumerate(pages_gt, start=1):
            gt_file = samples_dir / gt_rel
            if not gt_file.exists():
                missing_files.append(str(gt_file))
                continue

            # Render image or check for page image file
            page_img_path = samples_dir / f"{doc_id}.page{p_idx}.png"
            if not page_img_path.exists():
                missing_files.append(str(page_img_path))
                continue

            with open(page_img_path, "rb") as img_f:
                b64_img = base64.b64encode(img_f.read()).decode("utf-8")
            pages_payload.append(b64_img)

        if not pages_payload:
            continue

        payload = {"document_id": doc_id, "pages": pages_payload, "engine": engine}
        try:
            resp = requests.post(f"{service_url.rstrip('/')}/ocr", json=payload, timeout=120)
            resp.raise_for_status()
            res_json = resp.json()
        except Exception as e:
            logger.error(f"Failed to post document {doc_id} to OCR service: {e}")
            continue

        for page_res in res_json.get("pages", []):
            p_num = page_res["page_num"]
            ocr_text = page_res.get("text", "")
            gt_file = samples_dir / pages_gt[p_num - 1]
            gt_text = gt_file.read_text(encoding="utf-8").strip()

            eval_metrics = evaluate_ocr_result(ocr_text, gt_text)
            results.append({
                "doc_id": doc_id,
                "page_num": p_num,
                "cer": eval_metrics.get("cer"),
                "wer": eval_metrics.get("wer"),
                "f1_score": eval_metrics.get("f1"),
                "confidence": page_res.get("confidence", 0.0),
            })
            total_cer += eval_metrics["cer"]
            total_wer += eval_metrics["wer"]
            total_f1 += eval_metrics["f1"]
            evaluated_pages += 1

    if missing_files:
        raise FileNotFoundError(
            "Benchmark is incomplete; missing: " + ", ".join(sorted(set(missing_files)))
        )
    if evaluated_pages == 0:
        raise ValueError("Benchmark contains no evaluated pages")

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "engine_requested": engine,
        "total_evaluated_pages": evaluated_pages,
        "avg_cer": (total_cer / evaluated_pages) if evaluated_pages > 0 else None,
        "avg_wer": (total_wer / evaluated_pages) if evaluated_pages > 0 else None,
        "avg_f1": (total_f1 / evaluated_pages) if evaluated_pages > 0 else None,
        "page_results": results,
    }

    report_path = output_dir / f"ocr_service_eval_{engine}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Evaluation finished. Evaluated {evaluated_pages} pages. Summary saved to {report_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate ocr_service microservice endpoint.")
    parser.add_argument("--url", default="http://localhost:8001", help="Base URL of ocr_service")
    parser.add_argument("--manifest", default="datasets/urdu_ocr/manifests/manifest.json", help="Manifest JSON path")
    parser.add_argument("--samples", default="datasets/urdu_ocr/samples", help="Samples directory path")
    parser.add_argument("--out", default="datasets/urdu_ocr/reports", help="Output report directory")
    parser.add_argument(
        "--engine",
        choices=("tesseract", "paddleocr", "both"),
        default="tesseract",
        help="OCR engine to request, or both for a side-by-side comparison",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    engines = ("tesseract", "paddleocr") if args.engine == "both" else (args.engine,)
    summaries = {
        engine: evaluate_ocr_service(
            service_url=args.url,
            manifest_path=project_root / args.manifest,
            samples_dir=project_root / args.samples,
            output_dir=project_root / args.out,
            engine=engine,
        )
        for engine in engines
    }
    if len(summaries) == 2:
        comparison_path = project_root / args.out / f"ocr_service_comparison_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
        comparison_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Side-by-side comparison saved to %s", comparison_path)


if __name__ == "__main__":
    main()
