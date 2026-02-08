"""Script/language detection for OCR (Urdu vs English)."""
import logging
import re
from typing import Dict, Optional

import pytesseract
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Unicode ranges for Arabic script (including Urdu)
ARABIC_UNICODE_RANGES = [
    (0x0600, 0x06FF),  # Arabic block
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
]


def is_arabic_char(char: str) -> bool:
    """Check if character is in Arabic script (including Urdu)."""
    code_point = ord(char)
    for start, end in ARABIC_UNICODE_RANGES:
        if start <= code_point <= end:
            return True
    return False


def detect_script_dominance(pil_img: Image.Image) -> Dict[str, any]:
    """
    Detect script dominance (English vs Urdu vs Mixed).
    
    Returns:
        {
            "script": "eng" | "urd" | "mixed",
            "confidence": float (0.0-1.0),
            "method": "osd" | "char_ratio" | "fallback"
        }
    """
    if not settings.OCR_ENABLE_SCRIPT_DETECTION:
        return {
            "script": "eng",
            "confidence": 0.0,
            "method": "disabled"
        }
    
    # Method 1: Try Tesseract OSD (Orientation and Script Detection)
    try:
        osd_result = pytesseract.image_to_osd(pil_img, output_type=pytesseract.Output.DICT)
        
        # OSD returns script name (e.g., "Latin", "Arabic", etc.)
        script_name = osd_result.get("script", "").lower()
        script_conf = float(osd_result.get("script_confidence", 0))
        
        # Map script names to our codes
        if "arabic" in script_name:
            return {
                "script": "urd",  # Treat Arabic script as Urdu
                "confidence": script_conf / 100.0 if script_conf > 0 else 0.5,
                "method": "osd"
            }
        elif "latin" in script_name:
            return {
                "script": "eng",
                "confidence": script_conf / 100.0 if script_conf > 0 else 0.5,
                "method": "osd"
            }
        # If OSD returns something else, fall through to char_ratio
    except Exception as e:
        logger.debug(f"OSD detection failed: {e}, trying char_ratio method")
        # Fall through to char_ratio method
    
    # Method 2: Character ratio analysis (fallback)
    try:
        # Run quick OCR with English to get text sample
        # Use a smaller/downscaled version for speed
        test_img = pil_img.copy()
        # Downscale if too large (max 1000px on largest side)
        max_dim = max(test_img.size)
        if max_dim > 1000:
            scale = 1000 / max_dim
            new_size = (int(test_img.size[0] * scale), int(test_img.size[1] * scale))
            test_img = test_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Quick OCR with English (fast, doesn't need accuracy)
        config = "--psm 6 -l eng"  # Single uniform block, English
        try:
            sample_text = pytesseract.image_to_string(test_img, config=config, timeout=10)
        except Exception:
            # If OCR fails, fall back to default
            return {
                "script": "eng",
                "confidence": 0.0,
                "method": "fallback"
            }
        
        # Count Arabic script characters vs total characters
        total_chars = len([c for c in sample_text if c.isalpha()])
        if total_chars == 0:
            return {
                "script": "eng",
                "confidence": 0.0,
                "method": "char_ratio"
            }
        
        arabic_chars = sum(1 for c in sample_text if is_arabic_char(c))
        arabic_ratio = arabic_chars / total_chars if total_chars > 0 else 0.0
        
        # Thresholds
        if arabic_ratio > 0.3:  # More than 30% Arabic chars
            script = "urd"
            confidence = min(0.9, arabic_ratio * 1.5)  # Scale up ratio for confidence
        elif arabic_ratio > 0.1:  # 10-30% Arabic chars
            script = "mixed"
            confidence = arabic_ratio * 2.0
        else:  # Less than 10% Arabic chars
            script = "eng"
            confidence = 1.0 - arabic_ratio
        
        return {
            "script": script,
            "confidence": confidence,
            "method": "char_ratio"
        }
        
    except Exception as e:
        logger.warning(f"Character ratio detection failed: {e}, using fallback")
        # Fallback: assume English
        return {
            "script": "eng",
            "confidence": 0.0,
            "method": "fallback"
        }

