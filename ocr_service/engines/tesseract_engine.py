"""Tesseract OCR engine implementation (F4 fixes)."""
import logging

import numpy as np
from PIL import Image

from preprocessing import binarize_for_tesseract
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


def reconstruct_text_from_data(data: dict) -> str:
    """
    Reconstructs reading-order text from a single image_to_data dictionary pass.
    Respects block_num, par_num, and line_num boundaries.
    """
    lines: list[str] = []
    current_line: list[str] = []
    last_key: tuple[int, int, int] | None = None

    texts = data.get("text", [])
    block_nums = data.get("block_num", [])
    par_nums = data.get("par_num", [])
    line_nums = data.get("line_num", [])

    for idx, word in enumerate(texts):
        cleaned = (word or "").strip()
        if not cleaned:
            continue

        b_num = block_nums[idx] if idx < len(block_nums) else 0
        p_num = par_nums[idx] if idx < len(par_nums) else 0
        l_num = line_nums[idx] if idx < len(line_nums) else 0
        key = (b_num, p_num, l_num)

        if last_key is not None and key != last_key:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
            if key[0] != last_key[0]:  # New block space
                lines.append("")

        current_line.append(cleaned)
        last_key = key

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines).strip()


def run_tesseract(image: np.ndarray, psm: int = 3, dpi: int = 300) -> OcrPageResult:
    """
    Runs Tesseract OCR using a single image_to_data pass (F4 fix).
    Uses binarized image input, explicit DPI hint, and automatic layout (PSM 3).
    """
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

    # Convert to grayscale & apply Tesseract-specific dynamic binarization
    gray = image if image.ndim == 2 else np.dot(image[..., :3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)
    binary = binarize_for_tesseract(gray)
    pil_image = _to_pil(binary)

    # Config with explicit DPI, OEM 1 (LSTM), configurable PSM (default 3 auto layout)
    config = f"--oem 1 --psm {psm} --dpi {dpi} -l urd+eng"

    try:
        # SINGLE PASS: image_to_data only
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

    text = reconstruct_text_from_data(data)
    boxes: list[WordBox] = []
    confidences: list[float] = []

    for idx, word in enumerate(data.get("text", [])):
        cleaned = (word or "").strip()
        if not cleaned:
            continue

        confidence = _normalize_confidence(data.get("conf", [None])[idx])
        # Filter low noise confidence (< 0.15) from page average
        if confidence is not None and confidence >= 0.15:
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
