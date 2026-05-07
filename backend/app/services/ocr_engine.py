"""Unified OCR engine wrapper with script-aware language selection and enhanced preprocessing."""
import logging
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.core.config import settings
from app.services.ocr_preprocess import preprocess_for_ocr
from app.services.ocr_script_detect import detect_script_dominance

logger = logging.getLogger(__name__)


def _parse_osd_rotation(osd_output: str) -> Optional[int]:
    for line in osd_output.splitlines():
        if line.startswith("Rotate:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _should_retry_with_english(error: Exception) -> bool:
    message = str(error).lower()
    return "failed loading language" in message or "could not initialize" in message


def _run_tesseract_with_lang_fallback(ocr_callable, image: Image.Image, lang: str, **kwargs):
    try:
        return ocr_callable(image, lang=lang, **kwargs), lang, False
    except pytesseract.TesseractError as exc:
        if lang != "eng" and _should_retry_with_english(exc):
            logger.warning("Tesseract language '%s' unavailable, retrying with English", lang)
            return ocr_callable(image, lang="eng", **kwargs), "eng", True
        raise


@lru_cache(maxsize=1)
def _available_languages() -> tuple[str, ...]:
    return tuple(pytesseract.get_languages())


def normalize_confidence(conf: Optional[float]) -> Optional[float]:
    """
    Normalize confidence value to 0.0-1.0 range.

    Handles various input formats:
    - None -> None
    - < 0 -> None
    - 1.5 < conf <= 100 -> conf/100
    - 100 < conf <= 10000 -> (conf/100) then clamp to 1.0
    - Else treat as already 0..1
    - Always clamp final to [0.0, 1.0]

    Args:
        conf: Raw confidence value (may be 0-1, 0-100, or other range)

    Returns:
        Normalized confidence in [0.0, 1.0] or None
    """
    if conf is None:
        return None

    if conf < 0:
        return None

    if 1.5 < conf <= 100:
        normalized = conf / 100.0
    elif 100 < conf <= 10000:
        normalized = conf / 100.0
        if normalized > 1.0:
            normalized = 1.0
    else:
        normalized = conf

    normalized = max(0.0, min(1.0, normalized))
    return normalized


def pdf_to_image_dynamic(pdf_bytes: bytes, dpi_min: int = None, dpi_max: int = None, max_side: int = None) -> Tuple[Image.Image, int]:
    """
    Convert PDF to image with dynamic DPI selection.

    Args:
        pdf_bytes: PDF file bytes
        dpi_min: Minimum DPI (default: settings.OCR_DPI_MIN or OCR_DPI)
        dpi_max: Maximum DPI (default: settings.OCR_DPI_MAX or OCR_DPI)
        max_side: Maximum side length in pixels (default: settings.OCR_IMAGE_MAX_SIDE)

    Returns:
        Tuple of (PIL Image, DPI used)
    """
    dpi_min = dpi_min or getattr(settings, "OCR_DPI_MIN", settings.OCR_DPI)
    dpi_max = dpi_max or getattr(settings, "OCR_DPI_MAX", settings.OCR_DPI)
    max_side = max_side or settings.OCR_IMAGE_MAX_SIDE

    images = convert_from_bytes(pdf_bytes, dpi=dpi_min, fmt="png")
    if not images:
        raise ValueError("No pages found in PDF")

    image = images[0]
    width, height = image.size
    max_dimension = max(width, height)

    if max_dimension < max_side * 0.85 and dpi_max > dpi_min:
        try:
            images_higher = convert_from_bytes(pdf_bytes, dpi=dpi_max, fmt="png")
            if images_higher:
                image = images_higher[0]
                logger.debug(f"Using higher DPI {dpi_max} (image size: {max(image.size)})")
                return image, dpi_max
        except Exception as e:
            logger.warning(f"Failed to render at higher DPI {dpi_max}: {e}, using {dpi_min}")

    return image, dpi_min


def ocr_image(pil_img: Image.Image, dpi_used: int = None) -> Tuple[str, Optional[float], Dict[str, Any]]:
    """
    Unified OCR engine with script-aware language selection and enhanced preprocessing.

    Args:
        pil_img: PIL Image (will be preprocessed)
        dpi_used: DPI that was used to render the image (for metadata)

    Returns:
        Tuple of (extracted_text, confidence_score, metadata_dict)
    """
    dpi_used = dpi_used or getattr(settings, "OCR_DPI_MIN", settings.OCR_DPI)

    metadata: Dict[str, Any] = {
        "dpi_used": dpi_used,
        "preprocess_enabled": getattr(settings, "OCR_ENABLE_ENHANCED_PREPROCESS", settings.OCR_ENABLE_PREPROCESS),
        "psm": settings.OCR_PSM,
        "oem": settings.OCR_OEM,
    }

    if getattr(settings, "OCR_ENABLE_ENHANCED_PREPROCESS", False):
        processed_image = preprocess_for_ocr(pil_img)
        metadata["preprocess_method"] = "enhanced"
    else:
        from app.services.ocr import preprocess_image

        processed_image = preprocess_image(pil_img)
        metadata["preprocess_method"] = "basic"

    lang_used = settings.OCR_LANG
    rotation_angle: int | None = None
    orientation_osd_checked = False
    if getattr(settings, "OCR_ENABLE_SCRIPT_DETECTION", False):
        try:
            script_detect_result = detect_script_dominance(processed_image)
            script = script_detect_result.get("script", "eng")
            if script == "urd":
                lang_used = "urd+eng"
            elif script == "mixed":
                lang_used = "eng+urd"
            else:
                lang_used = "eng"
            rotation_angle = script_detect_result.get("rotation_angle")
            orientation_osd_checked = bool(script_detect_result.get("osd_attempted"))
            metadata["script_detection"] = script_detect_result
        except Exception as e:
            logger.warning(f"Script detection failed: {e}, using configured language")
            metadata["script_detection"] = {"error": str(e)}

    try:
        available_langs = _available_languages()
        lang_parts = lang_used.split("+")
        missing_langs = [lang for lang in lang_parts if lang not in available_langs]
        if missing_langs:
            logger.warning(f"Language(s) {missing_langs} not available, falling back to English")
            lang_used = "eng"
            metadata["lang_fallback"] = True
            metadata["missing_langs"] = missing_langs
        else:
            metadata["lang_fallback"] = False
    except Exception as e:
        logger.warning(f"Failed to check available languages: {e}, proceeding with {lang_used}")
        metadata["lang_fallback"] = False

    ocr_input_image = processed_image
    if getattr(settings, "OCR_ENABLE_ORIENTATION_DETECTION", False):
        if rotation_angle in {90, 180, 270}:
            ocr_input_image = processed_image.copy().rotate(rotation_angle, expand=True)
            metadata["orientation_rotation_applied"] = rotation_angle
            metadata["orientation_detection_method"] = "script_detection_osd"
        elif not orientation_osd_checked:
            try:
                osd_output = pytesseract.image_to_osd(processed_image)
                rotation_angle = _parse_osd_rotation(osd_output)
                metadata["orientation_detection_method"] = "ocr_osd"
                if rotation_angle in {90, 180, 270}:
                    ocr_input_image = processed_image.copy().rotate(rotation_angle, expand=True)
                    metadata["orientation_rotation_applied"] = rotation_angle
            except Exception as exc:
                logger.debug("Skipping OCR orientation detection: %s", exc)

    metadata["lang_used"] = lang_used

    try:
        config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM}"
        text, lang_used, runtime_fallback = _run_tesseract_with_lang_fallback(
            pytesseract.image_to_string,
            ocr_input_image,
            lang_used,
            config=config,
            timeout=settings.OCR_TIMEOUT_SECONDS,
        )
        metadata["lang_used"] = lang_used
        metadata["lang_fallback"] = metadata.get("lang_fallback", False) or runtime_fallback

        confidence_raw = None
        try:
            data, data_lang_used, data_runtime_fallback = _run_tesseract_with_lang_fallback(
                pytesseract.image_to_data,
                ocr_input_image,
                lang_used,
                config=config,
                output_type=pytesseract.Output.DICT,
                timeout=settings.OCR_TIMEOUT_SECONDS,
            )
            if data_runtime_fallback:
                metadata["lang_used"] = data_lang_used
                metadata["lang_fallback"] = True
            confidences = [int(c) for c in data.get("conf", []) if c != "-1" and str(c).isdigit()]
            if confidences:
                confidence_raw = sum(confidences) / len(confidences)
        except Exception:
            pass

        confidence_normalized = normalize_confidence(confidence_raw)
        metadata["confidence_raw"] = confidence_raw
        metadata["confidence_normalized"] = confidence_normalized

        return text.strip(), confidence_normalized, metadata
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        raise Exception(f"Tesseract OCR failed: {e}")
