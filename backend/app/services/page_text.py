"""Phase 10: Helper for getting effective page text (OCR or override)."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def get_effective_page_text(page) -> Dict[str, Any]:
    """
    Get effective text for a DocumentPage, preferring override over OCR.
    
    Args:
        page: DocumentPage instance
    
    Returns:
        Dict with:
        {
            "text": override text if present, else OCR text,
            "source": "override" | "ocr",
            "confidence": OCR confidence (from original OCR),
            "has_override": bool,
            "override": {
                "user_id": ...,
                "updated_at": ...,
                "reason": ...
            } | None
        }
    """
    has_override = bool(page.ocr_text_override)
    
    if has_override:
        text = page.ocr_text_override
        source = "override"
        override_info = {
            "user_id": str(page.ocr_override_user_id) if page.ocr_override_user_id else None,
            "updated_at": page.ocr_override_updated_at.isoformat() if page.ocr_override_updated_at else None,
            "reason": page.ocr_override_reason,
        }
    else:
        text = page.ocr_text
        source = "ocr"
        override_info = None
    
    return {
        "text": text or "",
        "source": source,
        "confidence": float(page.ocr_confidence) if page.ocr_confidence else None,
        "has_override": has_override,
        "override": override_info,
    }

