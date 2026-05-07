"""OCR service for extracting text from PDF pages using Tesseract."""
import logging
from typing import Optional, Tuple

import pytesseract
from PIL import Image, ImageFilter
from pdf2image import convert_from_bytes

from app.core.config import settings
from app.services.storage import get_s3_client

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """OCR processing error."""
    pass


def _safe_error_message(error: Exception) -> str:
    """Extract safe error message without secrets or full stack traces."""
    msg = str(error)
    if len(msg) > 500:
        msg = msg[:500] + "..."
    return msg


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


def download_page_pdf(minio_key: str) -> bytes:
    """Download page PDF bytes from MinIO."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=minio_key)
        return response["Body"].read()
    except Exception as e:
        raise OCRError(f"Failed to download PDF from MinIO: {e}")


def pdf_to_image(pdf_bytes: bytes) -> Tuple[Image.Image, int]:
    """Convert PDF bytes to PIL Image using poppler's pdftoppm.

    Returns:
        Tuple of (PIL Image, DPI used)
    """
    try:
        try:
            from app.services.ocr_engine import pdf_to_image_dynamic

            image, dpi_used = pdf_to_image_dynamic(
                pdf_bytes,
                dpi_min=getattr(settings, "OCR_DPI_MIN", settings.OCR_DPI),
                dpi_max=getattr(settings, "OCR_DPI_MAX", settings.OCR_DPI),
                max_side=settings.OCR_IMAGE_MAX_SIDE,
            )
            return image, dpi_used
        except ImportError:
            dpi_used = settings.OCR_DPI
            images = convert_from_bytes(pdf_bytes, dpi=dpi_used, fmt="png")
            if not images:
                raise OCRError("No pages found in PDF")
            return images[0], dpi_used
    except Exception as e:
        raise OCRError(f"Failed to convert PDF to image: {_safe_error_message(e)}")


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR results (P8 gold defaults).
    - Convert to grayscale
    - Auto-contrast
    - Light denoise (median filter)
    - Adaptive threshold (simple percentile-based)
    - Resize if too large or too small
    """
    if not settings.OCR_ENABLE_PREPROCESS:
        return image

    try:
        if image.mode != "L":
            image = image.convert("L")

        from PIL import ImageOps

        image = ImageOps.autocontrast(image)

        width, height = image.size
        if width > 100 and height > 100:
            try:
                image = image.filter(ImageFilter.MedianFilter(size=3))
            except Exception:
                pass

        max_side = settings.OCR_IMAGE_MAX_SIDE
        if width > max_side or height > max_side:
            if width > height:
                new_width = max_side
                new_height = int(height * (max_side / width))
            else:
                new_height = max_side
                new_width = int(width * (max_side / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        width, height = image.size
        min_size = 300
        if width < min_size or height < min_size:
            scale = max(min_size / width, min_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            if new_width > max_side or new_height > max_side:
                scale = min(max_side / width, max_side / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        try:
            import numpy as np

            img_array = np.array(image)
            threshold = np.percentile(img_array, 30)
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            image = Image.fromarray(img_array, mode="L")
        except ImportError:
            pass
        except Exception:
            pass

        return image
    except Exception as e:
        logger.warning(f"Preprocessing failed, using original image: {_safe_error_message(e)}")
        return image


def run_tesseract(image: Image.Image) -> Tuple[str, Optional[float], dict]:
    """
    Run Tesseract OCR on an image (P8 gold defaults).
    Returns (text, confidence_score, metadata).
    Confidence is a rough heuristic based on Tesseract output.
    """
    try:
        processed_image = preprocess_image(image)

        lang_used = settings.OCR_LANG
        try:
            available_langs = pytesseract.get_languages()
            if "urd" in lang_used.split("+") and "urd" not in available_langs:
                logger.warning("Urdu language data not available, falling back to English")
                lang_used = "eng"
        except Exception:
            pass

        config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM}"
        text, lang_used, lang_fallback = _run_tesseract_with_lang_fallback(
            pytesseract.image_to_string,
            processed_image,
            lang_used,
            config=config,
            timeout=settings.OCR_TIMEOUT_SECONDS,
        )

        confidence = None
        data_fallback = False
        try:
            data, _data_lang, data_fallback = _run_tesseract_with_lang_fallback(
                pytesseract.image_to_data,
                processed_image,
                lang_used,
                config=config,
                output_type=pytesseract.Output.DICT,
                timeout=settings.OCR_TIMEOUT_SECONDS,
            )
            confidences = [int(c) for c in data.get("conf", []) if c != "-1" and str(c).isdigit()]
            if confidences:
                confidence = sum(confidences) / len(confidences)
        except Exception:
            pass

        metadata = {
            "ocr_lang_used": lang_used,
            "ocr_lang_fallback": lang_fallback or data_fallback,
            "dpi_used": settings.OCR_DPI,
            "preprocess_enabled": settings.OCR_ENABLE_PREPROCESS,
        }

        return text.strip(), confidence, metadata
    except Exception as e:
        raise OCRError(f"Tesseract OCR failed: {_safe_error_message(e)}")


def ocr_page_pdf(minio_key: str) -> Tuple[str, Optional[float], dict]:
    """
    Full OCR pipeline for a page PDF stored in MinIO (P8 gold defaults + Urdu upgrade).

    Args:
        minio_key: The MinIO key for the page PDF.

    Returns:
        Tuple of (extracted_text, confidence_score, metadata)

    Raises:
        OCRError: If any step fails.
    """
    try:
        pdf_bytes = download_page_pdf(minio_key)
        image, dpi_used = pdf_to_image(pdf_bytes)

        try:
            from app.services.ocr_engine import ocr_image

            text, confidence, metadata = ocr_image(image, dpi_used=dpi_used)
        except ImportError:
            logger.warning("ocr_engine module not available, using legacy OCR")
            text, confidence, metadata = run_tesseract(image)
            if metadata and isinstance(metadata, dict):
                metadata["dpi_used"] = dpi_used

        return text, confidence, metadata
    except OCRError:
        raise
    except Exception as e:
        raise OCRError(f"OCR pipeline failed: {_safe_error_message(e)}")