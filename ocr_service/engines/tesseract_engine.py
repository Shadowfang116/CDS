import logging

import numpy as np
from PIL import Image

from schemas import OcrPageResult, WordBox

logger = logging.getLogger(__name__)


def _to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image, mode="L")
    return Image.fromarray(image, mode="RGB")


def _normalize_confidence(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if numeric < 0:
        return None
    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, numeric))


def run_tesseract(image: np.ndarray) -> OcrPageResult:
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not installed; returning unavailable OCR result")
        return OcrPageResult(
            engine_used="tesseract",
            quality_level="unavailable",
            warning_reason="pytesseract is not installed",
            confidence=0.0,
        )

    pil_image = _to_pil(image)
    config = "--oem 1 --psm 6 -l urd+eng"

    try:
        text = pytesseract.image_to_string(pil_image, config=config).strip()
        data = pytesseract.image_to_data(
            pil_image,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tesseract OCR failed: %s", exc)
        return OcrPageResult(
            engine_used="tesseract",
            quality_level="unavailable",
            warning_reason=f"Tesseract OCR failed: {exc}",
            confidence=0.0,
        )

    boxes: list[WordBox] = []
    confidences: list[float] = []

    for idx, word in enumerate(data.get("text", [])):
        cleaned = (word or "").strip()
        if not cleaned:
            continue

        confidence = _normalize_confidence(data.get("conf", [None])[idx])
        if confidence is not None:
            confidences.append(confidence)

        left = float(data.get("left", [0])[idx])
        top = float(data.get("top", [0])[idx])
        width = float(data.get("width", [0])[idx])
        height = float(data.get("height", [0])[idx])
        boxes.append(
            WordBox(
                text=cleaned,
                confidence=confidence,
                bbox=[left, top, left + width, top + height],
            )
        )

    average_confidence = sum(confidences) / len(confidences) if confidences else None
    return OcrPageResult(
        engine_used="tesseract",
        text=text,
        confidence=average_confidence,
        quality_level="fair" if text else "unusable",
        word_boxes=boxes,
    )
