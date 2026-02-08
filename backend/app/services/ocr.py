"""OCR service for extracting text from PDF pages using Tesseract."""
import io
import logging
import traceback
from typing import Tuple, Optional

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_bytes

from app.services.storage import get_s3_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """OCR processing error."""
    pass


def _safe_error_message(error: Exception) -> str:
    """Extract safe error message without secrets or full stack traces."""
    msg = str(error)
    # Remove potential secrets (base64-like strings, tokens)
    if len(msg) > 500:
        msg = msg[:500] + "..."
    return msg


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
        # Use dynamic DPI selection if available, otherwise fallback to legacy OCR_DPI
        try:
            from app.services.ocr_engine import pdf_to_image_dynamic
            image, dpi_used = pdf_to_image_dynamic(
                pdf_bytes,
                dpi_min=getattr(settings, 'OCR_DPI_MIN', settings.OCR_DPI),
                dpi_max=getattr(settings, 'OCR_DPI_MAX', settings.OCR_DPI),
                max_side=settings.OCR_IMAGE_MAX_SIDE
            )
            return image, dpi_used
        except ImportError:
            # Fallback to legacy method if new module not available
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
        # Convert to grayscale if not already
        if image.mode != 'L':
            image = image.convert('L')
        
        # Auto-contrast
        from PIL import ImageOps
        image = ImageOps.autocontrast(image)
        
        # Light denoise (median filter) - only if image is large enough
        width, height = image.size
        if width > 100 and height > 100:
            try:
                image = image.filter(ImageFilter.MedianFilter(size=3))
            except Exception:
                pass  # Skip if filter fails
        
        # Resize if too large (preserve aspect ratio)
        max_side = settings.OCR_IMAGE_MAX_SIDE
        if width > max_side or height > max_side:
            if width > height:
                new_width = max_side
                new_height = int(height * (max_side / width))
            else:
                new_height = max_side
                new_width = int(width * (max_side / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Ensure minimum size for OCR (at least 300px on smallest side)
        width, height = image.size
        min_size = 300
        if width < min_size or height < min_size:
            scale = max(min_size / width, min_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            # Don't exceed max_side
            if new_width > max_side or new_height > max_side:
                scale = min(max_side / width, max_side / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Simple adaptive threshold (percentile-based binarization)
        # Skip if numpy not available (optional enhancement)
        try:
            import numpy as np
            img_array = np.array(image)
            # Use 30th percentile as threshold (adjustable)
            threshold = np.percentile(img_array, 30)
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            image = Image.fromarray(img_array, mode='L')
        except ImportError:
            # Numpy not available - skip thresholding (not critical)
            pass
        except Exception:
            # If thresholding fails, skip it
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
        # Preprocess image
        processed_image = preprocess_image(image)
        
        # Build Tesseract config with gold defaults
        lang = settings.OCR_LANG
        # Check if lang includes "urd" and gracefully fall back if not available
        lang_used = lang
        try:
            # Try to verify language is available (best-effort)
            available_langs = pytesseract.get_languages()
            if "urd" in lang.split("+") and "urd" not in available_langs:
                logger.warning("Urdu language data not available, falling back to English")
                lang_used = "eng"
        except Exception:
            pass  # If we can't check, proceed with configured lang
        
        config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM} -l {lang_used}"
        text = pytesseract.image_to_string(processed_image, config=config, timeout=settings.OCR_TIMEOUT_SECONDS)
        
        # Get confidence data for heuristic
        confidence = None
        try:
            data = pytesseract.image_to_data(processed_image, config=config, output_type=pytesseract.Output.DICT, timeout=settings.OCR_TIMEOUT_SECONDS)
            confidences = [int(c) for c in data.get("conf", []) if c != "-1" and str(c).isdigit()]
            if confidences:
                confidence = sum(confidences) / len(confidences)
        except Exception:
            pass  # Confidence is optional
        
        metadata = {
            "ocr_lang_used": lang_used,
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
        # Step 1: Download PDF from MinIO
        pdf_bytes = download_page_pdf(minio_key)
        
        # Step 2: Convert PDF to image (with dynamic DPI)
        image, dpi_used = pdf_to_image(pdf_bytes)
        
        # Step 3: Run OCR using unified engine (includes preprocessing + script detection)
        try:
            from app.services.ocr_engine import ocr_image
            
            # Pass DPI used to ocr_image for metadata
            text, confidence, metadata = ocr_image(image, dpi_used=dpi_used)
            
        except ImportError:
            # Fallback to legacy method if new module not available
            logger.warning("ocr_engine module not available, using legacy OCR")
            text, confidence, metadata = run_tesseract(image)
            # Add DPI to metadata for legacy path
            if metadata and isinstance(metadata, dict):
                metadata["dpi_used"] = dpi_used
        
        return text, confidence, metadata
    except OCRError:
        raise  # Re-raise OCRError as-is
    except Exception as e:
        # Wrap unexpected errors
        raise OCRError(f"OCR pipeline failed: {_safe_error_message(e)}")

