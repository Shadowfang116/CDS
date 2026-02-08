"""HTTP client for HF Extractor service."""
import logging
import os
import re
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class HFExtractorEntity:
    """Entity extracted by HF Extractor."""
    def __init__(self, data: Dict[str, Any]):
        self.label = data.get("label", "")
        self.value = data.get("value", "")
        self.confidence = float(data.get("confidence", 0.0))
        self.source = data.get("source", {})
        self.evidence = data.get("evidence", {})
        # P17: OCR metadata (populated from response quality metrics)
        self.ocr_metadata = {}
        # P19: Quality and model metadata
        self.quality_metadata = {}
        # P19: Low confidence flag (for LayoutXLM entities below threshold but returned)
        self.low_confidence = data.get("low_confidence", None)


def _tokenize_ocr_text(ocr_text: str) -> tuple[List[str], List[List[float]]]:
    """Tokenize OCR text into words and create dummy bounding boxes.
    
    This is a placeholder implementation since OCR words/boxes aren't stored in DB yet.
    TODO: Replace with actual OCR word/box data when available.
    
    Args:
        ocr_text: The OCR text string
        
    Returns:
        Tuple of (words_list, boxes_list) where boxes are [x1, y1, x2, y2]
    """
    if not ocr_text:
        return [], []
    
    # Simple tokenization: split on whitespace
    words = re.findall(r'\S+', ocr_text)
    
    # Create dummy boxes (normalized 0-1 coordinates)
    # In a real implementation, these would come from OCR engine output
    boxes = []
    num_words = len(words)
    if num_words > 0:
        # Distribute words across a 1000x1000 grid (normalized)
        for i, word in enumerate(words):
            # Simple layout: 10 words per row
            row = i // 10
            col = i % 10
            x1 = float(col * 100) / 1000.0
            y1 = float(row * 30) / 1000.0
            x2 = float((col + 1) * 100) / 1000.0
            y2 = float((row + 1) * 30) / 1000.0
            boxes.append([x1, y1, x2, y2])
    
    return words, boxes


def extract_entities_page(
    doc_id: str,
    page_no: int,
    ocr_text: Optional[str] = None,
    ocr_engine: str = "tesseract",
    ocr_confidence: float = 0.0,
    labels: Optional[List[str]] = None,
    image_bytes: Optional[bytes] = None,
) -> List[HFExtractorEntity]:
    """
    Call HF Extractor service to extract entities from a document page.
    
    Args:
        doc_id: Document UUID as string
        page_no: Page number (1-indexed)
        ocr_text: OCR text for the page (optional; if not provided, hf-extractor will run OCR)
        ocr_engine: OCR engine name (paddleocr|tesseract|qaari)
        ocr_confidence: Page OCR confidence (0.0-1.0)
        labels: Optional list of labels to extract
        image_bytes: Image bytes (PNG/JPEG) - if provided, sent to hf-extractor for OCR
        
    Returns:
        List of extracted entities (empty list on error)
    """
    import base64
    
    extractor_url = os.getenv("HF_EXTRACTOR_URL", settings.HF_EXTRACTOR_URL)
    
    if not extractor_url:
        logger.warning("HF_EXTRACTOR_URL not configured, skipping HF extraction")
        return []
    
    # Encode image to base64 if provided
    image_base64 = ""
    if image_bytes:
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {str(e)}")
            return []
    
    # Build OCR data if provided, otherwise leave it null (hf-extractor will run OCR)
    ocr_data = None
    if ocr_text:
        # Tokenize OCR text into words and boxes (fallback if OCR data available)
        words, boxes = _tokenize_ocr_text(ocr_text)
        if words:
            ocr_data = {
                "engine": ocr_engine,
                "page_confidence": float(ocr_confidence) if ocr_confidence else 0.0,
                "words": words,
                "boxes": boxes,
                "normalized": True
            }
    
    # Get extractor options from config
    from app.core.config import settings
    extractor_version = settings.HF_EXTRACTOR_VERSION
    enable_layoutxlm = settings.HF_EXTRACTOR_ENABLE_LAYOUTXLM
    model_name_or_path = settings.HF_LAYOUTXLM_MODEL_PATH if settings.HF_LAYOUTXLM_MODEL_PATH else None
    
    # Build request payload
    payload = {
        "doc_id": doc_id,
        "page_no": page_no,
        "image": {
            "content_type": "image/png",
            "base64": image_base64
        },
        "ocr": ocr_data,  # Optional - if None, hf-extractor will run OCR
        "options": {
            "extractor_version": extractor_version,
            "return_token_spans": True,
            "language_hint": "mixed" if ocr_text and any(ord(c) > 0x0600 for c in ocr_text[:100]) else "en",  # Detect Urdu
            "labels": labels,  # None = extract all labels
            "enable_layoutxlm": enable_layoutxlm,  # P18: LayoutXLM gate
            "model_name_or_path": model_name_or_path,  # P18: Optional model path
        }
    }
    
    try:
        # Call HF Extractor service with timeout and retry
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{extractor_url}/v1/extract",
                json=payload,
            )
            response.raise_for_status()
            
            result = response.json()
            entities_data = result.get("entities", [])
            
            # Extract OCR metadata from response quality metrics (P17)
            quality = result.get("quality", {})
            ocr_metadata = {
                "ocr_page_confidence": quality.get("page_ocr_confidence"),
                "ocr_used_fallback": quality.get("ocr_used_fallback"),
                "ocr_engine_params": quality.get("ocr_engine_params"),
            }
            
            # P19: Extract quality and model metadata
            # P12: Include Qaari metadata
            quality_metadata = {
                "extractor_version_used": quality.get("extractor_version_used"),
                "model_name_or_path": quality.get("model_name_or_path"),
                "needs_manual_review": quality.get("needs_manual_review"),
                "corruption_detected": quality.get("corruption_detected"),
                "qaari_used": quality.get("qaari_used"),
                "ocr_text_only": quality.get("ocr_text_only"),
                "qaari_model_name_or_path": quality.get("qaari_model_name_or_path"),
            }
            
            entities = []
            for entity_data in entities_data:
                entity = HFExtractorEntity(entity_data)
                entity.ocr_metadata = ocr_metadata  # Attach OCR metadata to each entity
                entity.quality_metadata = quality_metadata  # P19: Attach quality metadata
                entities.append(entity)
            
            logger.info(
                f"HF extractor: doc_id={doc_id} page_no={page_no} "
                f"entities_received={len(entities)} "
                f"ocr_used_fallback={ocr_metadata.get('ocr_used_fallback')}"
            )
            
            return entities
            
    except httpx.TimeoutException:
        logger.error(
            f"HF extractor timeout: doc_id={doc_id} page_no={page_no} "
            f"url={extractor_url}"
        )
        return []
    except httpx.HTTPError as e:
        logger.error(
            f"HF extractor HTTP error: doc_id={doc_id} page_no={page_no} "
            f"error={str(e)} url={extractor_url}"
        )
        return []
    except Exception as e:
        logger.exception(
            f"HF extractor unexpected error: doc_id={doc_id} page_no={page_no} "
            f"error={str(e)}"
        )
        return []

