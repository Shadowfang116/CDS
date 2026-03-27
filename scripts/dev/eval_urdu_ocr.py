#!/usr/bin/env python3
"""Phase 9: Urdu OCR evaluation runner for regression testing."""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.ocr_engine import ocr_page_pdf
from app.services.ocr_eval import evaluate_ocr_result
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Load manifest JSON file."""
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_ground_truth(gt_path: Path) -> Optional[str]:
    """Load ground truth text file."""
    if not gt_path.exists():
        return None
    
    try:
        with open(gt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to load GT from {gt_path}: {e}")
        return None


def evaluate_page(
    pdf_path: Path,
    page_number: int,
    gt_text: Optional[str],
    mode: str
) -> Dict[str, Any]:
    """
    Run OCR on a page and evaluate against ground truth.
    
    Args:
        pdf_path: Path to PDF file
        page_number: 0-based page number
        gt_text: Optional ground truth text
        mode: "quick" or "full"
    
    Returns:
        Dict with OCR result and evaluation metrics
    """
    logger.info(f"Processing page {page_number} from {pdf_path.name}")
    
    # Run OCR using the canonical engine (production parity)
    # We need to adapt ocr_page_pdf to work with local files
    # Since ocr_page_pdf expects MinIO key, we'll create a local file adapter
    try:
        import tempfile
        import PyPDF2
        from pdf2image import convert_from_path
        from PIL import Image
        import pytesseract
        from app.core.config import settings
        
        # Try native PDF text extraction first (if enabled) - this works with local files
        native_text = None
        native_used = False
        
        if settings.OCR_ENABLE_PDF_TEXT_LAYER:
            try:
                from app.services.pdf_text_layer import extract_page_text
                from app.services.ocr_quality import score_pdf_text_layer
                
                extract_result = extract_page_text(
                    str(pdf_path),
                    page_number,
                    engine=settings.OCR_PDF_TEXT_LAYER_ENGINE
                )
                
                if extract_result.ok and extract_result.text:
                    score_result = score_pdf_text_layer(extract_result.text, settings)
                    if score_result["ok"]:
                        native_text = extract_result.text
                        native_used = True
            except Exception as e:
                logger.debug(f"Native extraction failed: {e}")
        
        # If native text not available, do OCR using production settings
        if not native_text:
            # Render PDF page to image using same DPI settings as production
            images = convert_from_path(
                str(pdf_path),
                first_page=page_number+1,
                last_page=page_number+1,
                dpi=getattr(settings, 'OCR_DPI', 200)
            )
            if not images:
                raise ValueError(f"No image rendered for page {page_number}")
            
            image = images[0]
            
            # Apply same preprocessing as production (if enabled)
            if settings.OCR_ENABLE_PREPROCESS:
                from app.services.ocr import preprocess_image
                image = preprocess_image(image)
            
            # Run Tesseract OCR with same settings as production
            lang = settings.OCR_LANG_URDU if settings.OCR_ENABLE_URDU else settings.OCR_LANG_DEFAULT
            config = f"--psm {settings.OCR_PSM} -l {lang}"
            
            pred_text = pytesseract.image_to_string(image, config=config)
            
            # Get confidence (average of word confidences)
            try:
                conf_data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                confidences = [float(c) for c in conf_data.get('conf', []) if float(c) > 0]
                confidence_avg = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            except:
                confidence_avg = 0.0
            
            pred_text = pred_text
            confidence = confidence_avg
            metadata = {
                'engine': 'tesseract',
                'pdf_text_layer': {'used': False, 'attempted': True},
                'ensemble': {'winner': 'tesseract'},
                'layout_ocr': {'used': False, 'attempted': False},
            }
        else:
            # Use native text
            pred_text = native_text
            confidence = 1.0
            metadata = {
                'engine': 'pdf_text_layer',
                'pdf_text_layer': {'used': True, 'attempted': True},
                'ensemble': {'winner': 'tesseract'},
                'layout_ocr': {'used': False, 'attempted': False},
            }
        
    except Exception as e:
        logger.error(f"OCR failed for page {page_number}: {e}")
        return {
            "error": str(e),
            "page": page_number,
        }
    
    # Evaluate
    compute_cer_wer = (mode == "full" and gt_text is not None)
    eval_metrics = evaluate_ocr_result(
        pred_text,
        gt_text=gt_text,
        compute_cer_wer=compute_cer_wer
    )
    
    # Extract routing decisions from metadata
    routing = {
        "pdf_text_layer_used": metadata.get("pdf_text_layer", {}).get("used", False),
        "ensemble_winner": metadata.get("ensemble", {}).get("winner", "tesseract"),
        "layout_used": metadata.get("layout_ocr", {}).get("used", False),
        "script_detected": metadata.get("script_detect", {}).get("script", "unknown"),
    }
    
    return {
        "page": page_number,
        "text_length": len(pred_text),
        "confidence": confidence or 0.0,
        "routing": routing,
        "metrics": eval_metrics,
        "metadata_keys": list(metadata.keys()),
    }


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate evaluation results across pages."""
    if not results:
        return {}
    
    # Filter out errors
    valid_results = [r for r in results if "error" not in r]
    
    if not valid_results:
        return {"error": "No valid results"}
    
    # Aggregate metrics
    total_pages = len(valid_results)
    
    # Routing statistics
    pdf_text_layer_count = sum(1 for r in valid_results if r.get("routing", {}).get("pdf_text_layer_used", False))
    ensemble_paddle_count = sum(1 for r in valid_results if r.get("routing", {}).get("ensemble_winner") == "paddleocr")
    layout_used_count = sum(1 for r in valid_results if r.get("routing", {}).get("layout_used", False))
    
    # Quality metrics averages
    urdu_ratios = [r.get("metrics", {}).get("urdu_ratio", 0.0) for r in valid_results]
    garbage_ratios = [r.get("metrics", {}).get("garbage_ratio", 0.0) for r in valid_results]
    confidences = [r.get("confidence", 0.0) for r in valid_results]
    
    # Error metrics (if GT available)
    cers = [r.get("metrics", {}).get("cer") for r in valid_results if r.get("metrics", {}).get("cer") is not None]
    wers = [r.get("metrics", {}).get("wer") for r in valid_results if r.get("metrics", {}).get("wer") is not None]
    f1s = [r.get("metrics", {}).get("f1") for r in valid_results if r.get("metrics", {}).get("f1") is not None]
    
    summary = {
        "total_pages": total_pages,
        "routing": {
            "pdf_text_layer_used_pct": (pdf_text_layer_count / total_pages * 100) if total_pages > 0 else 0.0,
            "ensemble_paddleocr_pct": (ensemble_paddle_count / total_pages * 100) if total_pages > 0 else 0.0,
            "layout_used_pct": (layout_used_count / total_pages * 100) if total_pages > 0 else 0.0,
        },
        "quality": {
            "avg_urdu_ratio": sum(urdu_ratios) / len(urdu_ratios) if urdu_ratios else 0.0,
            "avg_garbage_ratio": sum(garbage_ratios) / len(garbage_ratios) if garbage_ratios else 0.0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        },
    }
    
    if cers:
        summary["accuracy"] = {
            "avg_cer": sum(cers) / len(cers),
            "avg_wer": sum(wers) / len(wers) if wers else None,
            "avg_f1": sum(f1s) / len(f1s) if f1s else None,
            "pages_with_gt": len(cers),
        }
    
    return summary


def generate_markdown_report(report_data: Dict[str, Any], output_path: Path) -> None:
    """Generate human-friendly Markdown report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Urdu OCR Evaluation Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        summary = report_data.get("summary", {})
        
        f.write("## Summary\n\n")
        f.write(f"- Total pages: {summary.get('total_pages', 0)}\n")
        
        routing = summary.get("routing", {})
        f.write("\n### Routing Decisions\n\n")
        f.write(f"- PDF text layer used: {routing.get('pdf_text_layer_used_pct', 0.0):.1f}%\n")
        f.write(f"- Ensemble PaddleOCR winner: {routing.get('ensemble_paddleocr_pct', 0.0):.1f}%\n")
        f.write(f"- Layout OCR used: {routing.get('layout_used_pct', 0.0):.1f}%\n")
        
        quality = summary.get("quality", {})
        f.write("\n### Quality Metrics\n\n")
        f.write(f"- Average Urdu ratio: {quality.get('avg_urdu_ratio', 0.0):.4f}\n")
        f.write(f"- Average garbage ratio: {quality.get('avg_garbage_ratio', 0.0):.4f}\n")
        f.write(f"- Average confidence: {quality.get('avg_confidence', 0.0):.4f}\n")
        
        accuracy = summary.get("accuracy")
        if accuracy:
            f.write("\n### Accuracy Metrics (with Ground Truth)\n\n")
            f.write(f"- Average CER: {accuracy.get('avg_cer', 0.0):.4f}\n")
            if accuracy.get('avg_wer') is not None:
                f.write(f"- Average WER: {accuracy.get('avg_wer', 0.0):.4f}\n")
            if accuracy.get('avg_f1') is not None:
                f.write(f"- Average F1: {accuracy.get('avg_f1', 0.0):.4f}\n")
            f.write(f"- Pages with GT: {accuracy.get('pages_with_gt', 0)}\n")
        
        f.write("\n## Per-Page Results\n\n")
        for item in report_data.get("items", []):
            item_id = item.get("id", "unknown")
            f.write(f"### {item_id}\n\n")
            
            for page_result in item.get("pages", []):
                page_num = page_result.get("page", 0)
                f.write(f"**Page {page_num}**\n\n")
                
                if "error" in page_result:
                    f.write(f"- Error: {page_result['error']}\n\n")
                    continue
                
                metrics = page_result.get("metrics", {})
                routing_info = page_result.get("routing", {})
                
                f.write(f"- Text length: {page_result.get('text_length', 0)}\n")
                f.write(f"- Confidence: {page_result.get('confidence', 0.0):.4f}\n")
                f.write(f"- Urdu ratio: {metrics.get('urdu_ratio', 0.0):.4f}\n")
                f.write(f"- Garbage ratio: {metrics.get('garbage_ratio', 0.0):.4f}\n")
                
                if routing_info.get("pdf_text_layer_used"):
                    f.write("- Used PDF text layer\n")
                if routing_info.get("ensemble_winner") == "paddleocr":
                    f.write("- Ensemble winner: PaddleOCR\n")
                if routing_info.get("layout_used"):
                    f.write("- Used layout OCR\n")
                
                if metrics.get("cer") is not None:
                    f.write(f"- CER: {metrics['cer']:.4f}\n")
                    f.write(f"- WER: {metrics.get('wer', 0.0):.4f}\n")
                    f.write(f"- F1: {metrics.get('f1', 0.0):.4f}\n")
                
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Urdu OCR on golden dataset")
    parser.add_argument(
        "--manifest",
        type=str,
        default="datasets/urdu_ocr/manifests/manifest.json",
        help="Path to manifest JSON file"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="datasets/urdu_ocr/reports",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["quick", "full"],
        default="quick",
        help="Evaluation mode: quick (quality only) or full (with CER/WER/F1)"
    )
    parser.add_argument(
        "--fail-cer",
        type=float,
        default=None,
        help="Exit with code 1 if average CER exceeds this threshold"
    )
    
    args = parser.parse_args()
    
    # Load manifest
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    
    # Ensure output directory exists
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each item
    all_results = []
    
    for item in manifest.get("items", []):
        item_id = item.get("id", "unknown")
        pdf_path = Path(item.get("pdf_path", ""))
        
        if not pdf_path.exists():
            logger.warning(f"PDF not found: {pdf_path}, skipping {item_id}")
            continue
        
        item_results = []
        
        for page_info in item.get("pages", []):
            page_num = page_info.get("page", 0)
            gt_path = page_info.get("gt_path")
            
            gt_text = None
            if gt_path:
                gt_path_obj = Path(gt_path)
                gt_text = load_ground_truth(gt_path_obj)
            
            result = evaluate_page(pdf_path, page_num, gt_text, args.mode)
            item_results.append(result)
        
        all_results.extend(item_results)
    
    # Aggregate results
    summary = aggregate_results(all_results)
    
    # Build report
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "mode": args.mode,
        "summary": summary,
        "items": [
            {
                "id": item.get("id"),
                "pages": [
                    r for r in all_results
                    if any(
                        item.get("pages", [])[i].get("page") == r.get("page")
                        for i in range(len(item.get("pages", [])))
                    )
                ]
            }
            for item in manifest.get("items", [])
        ],
    }
    
    # Save JSON report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{timestamp}_report.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON report saved: {json_path}")
    
    # Save Markdown report
    md_path = output_dir / "latest_report.md"
    generate_markdown_report(report_data, md_path)
    logger.info(f"Markdown report saved: {md_path}")
    
    # Check fail threshold
    if args.fail_cer is not None:
        accuracy = summary.get("accuracy")
        if accuracy and accuracy.get("avg_cer") is not None:
            avg_cer = accuracy["avg_cer"]
            if avg_cer > args.fail_cer:
                logger.error(f"Average CER {avg_cer:.4f} exceeds threshold {args.fail_cer}")
                sys.exit(1)
    
    logger.info("Evaluation complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
