"""PaddleOCR engine adapter used for side-by-side CDS evaluation."""
import json
import logging
import os
from functools import lru_cache
from typing import Any

import numpy as np

from schemas import OcrPageResult, WordBox
from quality import score_page

logger = logging.getLogger(__name__)


def _normalize_confidence(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0:
        return None
    if numeric > 1.0:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _as_mapping(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    payload = getattr(result, "json", None)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    return {
        key: getattr(result, key)
        for key in ("rec_texts", "rec_scores", "rec_boxes")
        if hasattr(result, key)
    }


def _box_coordinates(box: Any) -> list[float]:
    values = np.asarray(box).reshape(-1).tolist()
    if len(values) >= 8:
        xs = values[0::2]
        ys = values[1::2]
        return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
    if len(values) >= 4:
        return [float(values[0]), float(values[1]), float(values[2]), float(values[3])]
    return []


def _parse_prediction(prediction: Any) -> tuple[str, list[WordBox]]:
    mapping = _as_mapping(prediction)
    texts = mapping.get("rec_texts", [])
    scores = mapping.get("rec_scores", [])
    boxes = mapping.get("rec_boxes", [])

    if texts:
        word_boxes = [
            WordBox(
                text=str(text).strip(),
                confidence=_normalize_confidence(scores[index] if index < len(scores) else None),
                bbox=_box_coordinates(boxes[index]) if index < len(boxes) else [],
            )
            for index, text in enumerate(texts)
            if str(text).strip()
        ]
        return "\n".join(box.text for box in word_boxes), word_boxes

    # Compatibility with the older PaddleOCR .ocr() response shape.
    lines = prediction if isinstance(prediction, list) else []
    if lines and isinstance(lines[0], list) and lines[0] and isinstance(lines[0][0], list):
        lines = lines[0]
    word_boxes = []
    for line in lines:
        if len(line) < 2:
            continue
        box, recognized = line[0], line[1]
        text, score = recognized if isinstance(recognized, (list, tuple)) else (recognized, None)
        cleaned = str(text).strip()
        if cleaned:
            word_boxes.append(WordBox(text=cleaned, confidence=_normalize_confidence(score), bbox=_box_coordinates(box)))
    return "\n".join(box.text for box in word_boxes), word_boxes


@lru_cache(maxsize=1)
def _get_ocr():
    # PaddlePaddle 3.x can select a oneDNN kernel that is not implemented for
    # some CPU inference graphs used by PaddleOCR. Keep this experiment stable
    # on the same CPU-only Docker profile as Tesseract.
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang="ur",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )


def run_paddleocr(image: np.ndarray) -> OcrPageResult:
    """Run local PaddleOCR using the Urdu multilingual recognition model."""
    try:
        ocr = _get_ocr()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PaddleOCR is unavailable: %s", exc)
        return OcrPageResult(
            engine_used="paddleocr",
            quality_level="unavailable",
            warning_reason=f"PaddleOCR is unavailable: {exc}",
            confidence=0.0,
        )

    try:
        if hasattr(ocr, "predict"):
            predictions = list(ocr.predict(image))
        else:
            predictions = ocr.ocr(image, cls=True)
        texts: list[str] = []
        word_boxes: list[WordBox] = []
        for prediction in predictions:
            text, boxes = _parse_prediction(prediction)
            if text:
                texts.append(text)
            word_boxes.extend(boxes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PaddleOCR failed: %s", exc)
        return OcrPageResult(
            engine_used="paddleocr",
            quality_level="unavailable",
            warning_reason=f"PaddleOCR failed: {exc}",
            confidence=0.0,
        )

    confidences = [box.confidence for box in word_boxes if box.confidence is not None]
    text = "\n".join(texts).strip()
    quality = score_page(text, word_boxes)
    return OcrPageResult(
        engine_used="paddleocr",
        text=text,
        confidence=sum(confidences) / len(confidences) if confidences else None,
        quality_score=quality.quality_score,
        quality_level=quality.quality_level,
        warning_reason=quality.warning_reason,
        word_boxes=word_boxes,
    )
