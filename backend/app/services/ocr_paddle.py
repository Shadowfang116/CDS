"""Phase 4: PaddleOCR engine wrapper for ensemble mode."""
import logging
from typing import Any, Dict, Tuple, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Global singleton for PaddleOCR instance
_paddle_ocr_instance: Optional[Any] = None
_paddle_ocr_initialized = False
_paddle_ocr_error: Optional[str] = None


def _lazy_init_paddle(settings_obj) -> Tuple[Optional[Any], Optional[str]]:
    """
    Lazy initialization of PaddleOCR instance (singleton).
    
    Args:
        settings_obj: Settings object with PaddleOCR config
    
    Returns:
        Tuple of (paddle_ocr_instance_or_none, error_message_or_none)
    """
    global _paddle_ocr_instance, _paddle_ocr_initialized, _paddle_ocr_error
    
    if _paddle_ocr_initialized:
        return _paddle_ocr_instance, _paddle_ocr_error
    
    _paddle_ocr_initialized = True
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR with settings
        _paddle_ocr_instance = PaddleOCR(
            use_angle_cls=settings_obj.OCR_PADDLE_USE_ANGLE_CLS,
            lang=settings_obj.OCR_PADDLE_LANG,
            use_gpu=settings_obj.OCR_PADDLE_USE_GPU,
            show_log=False,  # Suppress verbose output
        )
        
        logger.info("PaddleOCR initialized successfully")
        return _paddle_ocr_instance, None
        
    except ImportError as e:
        _paddle_ocr_error = "PADDLE_NOT_INSTALLED"
        logger.warning(f"PaddleOCR not installed: {e}. Install with: pip install paddleocr paddlepaddle")
        return None, _paddle_ocr_error
        
    except Exception as e:
        _paddle_ocr_error = f"PADDLE_INIT_FAILED: {str(e)[:200]}"
        logger.error(f"PaddleOCR initialization failed: {e}")
        return None, _paddle_ocr_error


def ocr_image_paddle(pil_image:
    Image.Image, settings_obj) -> Tuple[str, float, Dict[str, Any]]:
    """
    Run PaddleOCR on a PIL image.
    
    Args:
        pil_image: PIL Image to OCR (should be RGB or L)
        settings_obj: Settings object with PaddleOCR config
    
    Returns:
        Tuple of (text, confidence, metadata)
        - text: Extracted text (joined lines with "
")
        - confidence: Average confidence score (0.0-1.0)
        - metadata: Dict with engine, lang_used, lines, error (if any)
    """
    metadata: Dict[str, Any] = {
        "engine": "paddleocr",
        "lang_used": settings_obj.OCR_PADDLE_LANG,
    }
    
    # Lazy init PaddleOCR
    paddle_ocr, init_error = _lazy_init_paddle(settings_obj)
    
    if paddle_ocr is None:
        error_msg = init_error or "PADDLE_NOT_INSTALLED"
        metadata["error"] = error_msg
        logger.warning(f"PaddleOCR not available: {error_msg}")
        return "", 0.0, metadata
    
    try:
        # Convert PIL Image to numpy array (RGB)
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        img_np = np.array(pil_image)
        
        # Run PaddleOCR
        use_angle_cls = settings_obj.OCR_PADDLE_USE_ANGLE_CLS
        result = paddle_ocr.ocr(img_np, cls=use_angle_cls)
        
        # Extract text lines in reading order
        text_lines = []
        confidences = []
        
        if result and len(result) > 0 and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    # line format: [[bbox], (text, confidence)]
                    text_info = line[1]
                    if text_info:
                        text = text_info[0]
                        conf = float(text_info[1]) if len(text_info) > 1 else 0.0
                        text_lines.append(text)
                        confidences.append(conf)
        
        # Join lines with newline
        text = "\n".join(text_lines)
        
        # Calculate average confidence
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0..1
        
        metadata["lines"] = len(text_lines)
        metadata["line_confidences"] = confidences[:10] if len(confidences) > 10 else confidences  # Sample
        
        return text, confidence, metadata
        
    except Exception as e:
        error_msg = str(e)[:300]  # Limit error message length
        metadata["error"] = "PADDLE_OCR_FAILED"
        metadata["detail"] = error_msg
        logger.error(f"PaddleOCR failed: {e}")
        return "", 0.0, metadata

