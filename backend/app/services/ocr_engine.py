"""Unified OCR engine wrapper with script-aware language selection and enhanced preprocessing."""
import logging
from typing import Tuple, Optional, Dict, Any

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.core.config import settings
from app.services.ocr_preprocess import preprocess_for_ocr
from app.services.ocr_script_detect import detect_script_dominance

logger = logging.getLogger(__name__)


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
    
    # If confidence is in 1.5-100 range, treat as percentage
    if 1.5 < conf <= 100:
        normalized = conf / 100.0
    # If confidence is > 100 but <= 10000, divide by 100 then clamp
    elif 100 < conf <= 10000:
        normalized = (conf / 100.0)
        if normalized > 1.0:
            normalized = 1.0
    else:
        # Treat as already 0..1 range
        normalized = conf
    
    # Clamp to [0.0, 1.0]
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
    dpi_min = dpi_min or getattr(settings, 'OCR_DPI_MIN', settings.OCR_DPI)
    dpi_max = dpi_max or getattr(settings, 'OCR_DPI_MAX', settings.OCR_DPI)
    max_side = max_side or settings.OCR_IMAGE_MAX_SIDE
    
    # Start with minimum DPI
    images = convert_from_bytes(pdf_bytes, dpi=dpi_min, fmt="png")
    if not images:
        raise ValueError("No pages found in PDF")
    
    image = images[0]
    
    # Check if we should use higher DPI
    width, height = image.size
    max_dimension = max(width, height)
    
    # If image is significantly smaller than max_side (85% threshold), try higher DPI
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
    dpi_used = dpi_used or getattr(settings, 'OCR_DPI_MIN', settings.OCR_DPI)
    
    metadata: Dict[str, Any] = {
        "dpi_used": dpi_used,
        "preprocess_enabled": getattr(settings, 'OCR_ENABLE_ENHANCED_PREPROCESS', settings.OCR_ENABLE_PREPROCESS),
        "psm": settings.OCR_PSM,
        "oem": settings.OCR_OEM,
    }
    
    # Step 1: Preprocess image
    if getattr(settings, 'OCR_ENABLE_ENHANCED_PREPROCESS', False):
        processed_image = preprocess_for_ocr(pil_img)
        metadata["preprocess_method"] = "enhanced"
    else:
        # Fallback to basic preprocessing (existing behavior)
        from app.services.ocr import preprocess_image
        processed_image = preprocess_image(pil_img)
        metadata["preprocess_method"] = "basic"
    
    # Step 2: Script detection and language selection
    lang_used = settings.OCR_LANG  # Default from config
    script_detect_result = None
    
    if getattr(settings, 'OCR_ENABLE_SCRIPT_DETECTION', False):
        try:
            script_detect_result = detect_script_dominance(processed_image)
            script = script_detect_result.get("script", "eng")
            
            # Override language based on script detection
            # P17: Use urd+eng for Urdu (not just urd) to handle mixed content
            if script == "urd":
                lang_used = "urd+eng"  # Default to urd+eng for Urdu documents
            elif script == "mixed":
                lang_used = "eng+urd"
            else:
                lang_used = "eng"
            
            metadata["script_detection"] = script_detect_result
            
        except Exception as e:
            logger.warning(f"Script detection failed: {e}, using configured language")
            metadata["script_detection"] = {"error": str(e)}
    
    # Step 3: Validate language is available
    try:
        available_langs = pytesseract.get_languages()
        # Handle composite languages (e.g., "eng+urd")
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
    
    metadata["lang_used"] = lang_used
    
    # Step 4: Run Tesseract OCR
    try:
        config = f"--oem {settings.OCR_OEM} --psm {settings.OCR_PSM} -l {lang_used}"
        text = pytesseract.image_to_string(processed_image, config=config, timeout=settings.OCR_TIMEOUT_SECONDS)
        
        # Get confidence from image_to_data
        confidence_raw = None
        try:
            data = pytesseract.image_to_data(
                processed_image,
                config=config,
                output_type=pytesseract.Output.DICT,
                timeout=settings.OCR_TIMEOUT_SECONDS
            )
            confidences = [int(c) for c in data.get("conf", []) if c != "-1" and str(c).isdigit()]
            if confidences:
                confidence_raw = sum(confidences) / len(confidences)
        except Exception:
            pass  # Confidence is optional
        
        # Normalize confidence to 0.0-1.0
        confidence_normalized = normalize_confidence(confidence_raw)
        
        # Add confidence metadata
        metadata["confidence_raw"] = confidence_raw
        metadata["confidence_normalized"] = confidence_normalized
        
        return text.strip(), confidence_normalized, metadata
        
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        raise Exception(f"Tesseract OCR failed: {e}")

