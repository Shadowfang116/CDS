"""FastAPI application for HF Extractor service."""
import base64
import logging
import os
from typing import List, Optional
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from schemas import (
    ExtractRequest,
    ExtractResponse,
    ExtractedEntity,
    ExtractorInfo,
    EntitySource,
    EntityEvidence,
    QualityMetrics,
    HealthResponse,
    OCRData,
    VALID_LABELS,
)
from extractors import extract_all_entities, _get_snippet, _is_mojibake_or_corrupted
from ocr_router import choose_ocr

# Optional LayoutXLM import (safe - will only be called if enabled)
try:
    from layoutxlm_infer import infer_layoutxlm_entities
    LAYOUTXLM_AVAILABLE = True
except ImportError:
    LAYOUTXLM_AVAILABLE = False
    logger.debug("LayoutXLM inference module not available (ML deps not installed)")

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HF Extractor Service",
    description="Hugging Face-based document entity extraction service",
    version="1.0.0"
)

# Environment variables with defaults
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/layoutxlm-base")
EXTRACTOR_VERSION = os.getenv("EXTRACTOR_VERSION", "layoutxlm-v1")
DEVICE = os.getenv("DEVICE", "cpu")


def normalize_bbox_to_1000(bbox: List[float], image_width: float = 1000.0, image_height: float = 1000.0) -> List[int]:
    """Normalize bbox to 0-1000 scale.
    
    Args:
        bbox: [x1, y1, x2, y2] in original coordinates
        image_width: Image width (default 1000 for normalized boxes)
        image_height: Image height (default 1000 for normalized boxes)
        
    Returns:
        Normalized bbox as [x1, y1, x2, y2] scaled to 0-1000
    """
    if len(bbox) < 4:
        return [0, 0, 0, 0]
    
    # If boxes are already normalized (0-1), scale to 0-1000
    # Otherwise assume they're in pixel coordinates and normalize
    if bbox[2] <= 1.0 and bbox[3] <= 1.0:
        # Already normalized to 0-1
        scale_x = 1000.0
        scale_y = 1000.0
    else:
        # Pixel coordinates, normalize using image dimensions
        scale_x = 1000.0 / image_width if image_width > 0 else 1.0
        scale_y = 1000.0 / image_height if image_height > 0 else 1.0
    
    return [
        int(bbox[0] * scale_x),
        int(bbox[1] * scale_y),
        int(bbox[2] * scale_x),
        int(bbox[3] * scale_y),
    ]


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(ok=True)


@app.post("/v1/extract", response_model=ExtractResponse)
async def extract(request: ExtractRequest, http_request: Request):
    """Extract entities from document page.
    
    If OCR data is missing or empty, runs OCR on the provided image.
    
    Args:
        request: Extraction request with image (required) and optional OCR data
        http_request: HTTP request object for logging
        
    Returns:
        Extraction response with entities
    """
    doc_id = request.doc_id
    page_no = request.page_no
    
    # Decode image from base64
    try:
        image_bytes = base64.b64decode(request.image.base64)
    except Exception as e:
        logger.error(f"Failed to decode image base64: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid image base64 encoding")
    
    # Determine if we need to run OCR
    ocr_data = request.ocr
    used_ocr_engine = None
    word_count = 0
    image_width = 0
    image_height = 0
    
    # OCR routing metadata
    ocr_used_fallback = False
    ocr_engine_params = None
    ocr_attempts = []
    # P12: Qaari flags (initialized from OCR result if OCR was run)
    qaari_used = False
    ocr_text_only = False
    qaari_model_name_or_path = None
    
    if ocr_data is None or not ocr_data.words or (ocr_data.boxes is None and len(ocr_data.words) == 0):
        # Run OCR routing (with fallback if needed)
        logger.info(
            f"OCR needed: doc_id={doc_id} page_no={page_no} "
            f"ocr_provided={ocr_data is not None}"
        )
        
        ocr_result = choose_ocr(image_bytes, request.options)
        
        used_ocr_engine = ocr_result["selected_engine"]
        word_count = len(ocr_result["words"])
        image_width = ocr_result.get("image_width", 0)
        image_height = ocr_result.get("image_height", 0)
        page_confidence = ocr_result["selected_page_confidence"]
        ocr_used_fallback = ocr_result["used_fallback"]
        ocr_engine_params = ocr_result["selected_engine_params"]
        ocr_attempts = ocr_result["attempts"]
        
        # P12: Extract Qaari flags
        qaari_used = ocr_result.get("qaari_used", False)
        ocr_text_only = ocr_result.get("ocr_text_only", False)
        qaari_model_name_or_path = ocr_result.get("qaari_model_name_or_path")
        
        # Log OCR routing decision
        logger.info(
            f"HF_EXTRACTOR_OCR: doc_id={doc_id} page={page_no} "
            f"used_fallback={ocr_used_fallback} "
            f"qaari_used={qaari_used} ocr_text_only={ocr_text_only} "
            f"selected_conf={page_confidence:.3f} "
            f"selected_engine={used_ocr_engine} "
            f"attempts={len(ocr_attempts)}"
        )
        
        # Create OCRData from OCR result
        ocr_data = OCRData(
            engine=used_ocr_engine,
            page_confidence=page_confidence,
            words=ocr_result["words"],
            boxes=ocr_result.get("boxes"),  # Can be None for text-only OCR
            normalized=False,  # Boxes are in pixel coordinates (if present)
        )
    else:
        # Use provided OCR data
        used_ocr_engine = ocr_data.engine
        word_count = len(ocr_data.words)
        page_confidence = ocr_data.page_confidence
        
        # If image dimensions not provided, try to get from image
        if image_bytes:
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(image_bytes))
                image_width, image_height = img.size
            except Exception:
                # Fallback: assume normalized boxes (0-1 scale)
                image_width = 1000.0
                image_height = 1000.0
        else:
            image_width = 1000.0
            image_height = 1000.0
    
    # Prepare boxes_norm_1000 for LayoutXLM (if needed)
    # P12: Handle text-only OCR (boxes=None)
    boxes_norm_1000 = None
    if ocr_data.boxes is not None:
        boxes_norm_1000 = []
        if image_width > 0 and image_height > 0:
            for bbox_px in ocr_data.boxes:
                bbox_norm = normalize_bbox_to_1000(bbox_px, image_width, image_height)
                boxes_norm_1000.append(bbox_norm)
        else:
            # Fallback: assume boxes are already normalized or use dummy
            boxes_norm_1000 = [[0, 0, 0, 0]] * len(ocr_data.words) if ocr_data.words else []
    
    # P19: Check for corruption in OCR words
    corruption_detected = False
    if ocr_data.words:
        # Check a sample of words for corruption (first 50 or all if fewer)
        sample_words = ocr_data.words[:50]
        corrupted_count = sum(1 for word in sample_words if _is_mojibake_or_corrupted(word))
        corruption_ratio = corrupted_count / len(sample_words) if sample_words else 0.0
        corruption_detected = corruption_ratio > 0.05  # >5% corrupted tokens
    
    # Determine extractor path
    requested_version = request.options.extractor_version or "rules-v1"
    enable_layoutxlm = request.options.enable_layoutxlm or False
    extractor_version_used = "rules-v1"
    model_loaded = False
    model_name_or_path_used = None
    fallback_reason = None
    
    extracted_data = []
    
    # Try LayoutXLM if requested and enabled (skip if text-only OCR)
    if requested_version == "layoutxlm-v1" and enable_layoutxlm and boxes_norm_1000 is not None:
        logger.info(
            f"HF_EXTRACTOR_MODEL: doc_id={doc_id} page={page_no} "
            f"requested=layoutxlm-v1 enabled={enable_layoutxlm}"
        )
        
        if not LAYOUTXLM_AVAILABLE:
            fallback_reason = "LayoutXLM module not available (ML deps not installed)"
            logger.warning(f"HF_EXTRACTOR_MODEL: {fallback_reason}")
        else:
            try:
                entities_lxm, meta = infer_layoutxlm_entities(
                    image_bytes=image_bytes,
                    words=ocr_data.words,
                    boxes_norm_1000=boxes_norm_1000,
                    options=request.options,
                )
                
                model_loaded = meta.get("model_loaded", False)
                model_name_or_path_used = meta.get("model_name_or_path")
                
                if entities_lxm:
                    # Use LayoutXLM entities
                    extracted_data = entities_lxm
                    extractor_version_used = "layoutxlm-v1"
                    
                    # Compute pixel bboxes from OCR boxes if available
                    for entity in extracted_data:
                        if entity.token_indices and ocr_data.boxes:
                            # Compute union bbox from OCR pixel boxes
                            selected_boxes = [
                                ocr_data.boxes[i] for i in entity.token_indices 
                                if i < len(ocr_data.boxes)
                            ]
                            if selected_boxes:
                                min_x1 = min(box[0] for box in selected_boxes)
                                min_y1 = min(box[1] for box in selected_boxes)
                                max_x2 = max(box[2] for box in selected_boxes)
                                max_y2 = max(box[3] for box in selected_boxes)
                                entity.bbox = [min_x1, min_y1, max_x2, max_y2]
                    
                    logger.info(
                        f"HF_EXTRACTOR_MODEL: doc_id={doc_id} page={page_no} "
                        f"used=layoutxlm-v1 model_loaded={model_loaded} "
                        f"entities={len(entities_lxm)}"
                    )
                else:
                    # LayoutXLM returned no entities, fall back to rules
                    fallback_reason = meta.get("error", "No entities extracted by LayoutXLM")
                    logger.info(
                        f"HF_EXTRACTOR_MODEL: doc_id={doc_id} page={page_no} "
                        f"fallback_to_rules reason={fallback_reason}"
                    )
                    
            except Exception as e:
                fallback_reason = f"LayoutXLM inference error: {str(e)}"
                logger.error(
                    f"HF_EXTRACTOR_MODEL: doc_id={doc_id} page={page_no} "
                    f"fallback_to_rules reason={fallback_reason}",
                    exc_info=True
                )
    
    # Use rules extractors if LayoutXLM not used or failed
    if not extracted_data:
        extractor_version_used = "rules-v1"
        if fallback_reason:
            logger.info(
                f"HF_EXTRACTOR_MODEL: doc_id={doc_id} page={page_no} "
                f"fallback_to_rules reason={fallback_reason}"
            )
        
        labels_to_extract = request.options.labels
        if labels_to_extract:
            labels_to_extract = [l for l in labels_to_extract if l in VALID_LABELS]
        
        extracted_data = extract_all_entities(
            words=ocr_data.words,
            boxes=ocr_data.boxes,
            labels=labels_to_extract,
            image_width=image_width,
            image_height=image_height,
        )
    
    # Structured logging (extraction phase)
    logger.info(
        f"HF_EXTRACTOR_EXTRACT: doc_id={doc_id} page={page_no} "
        f"extractor_version_used={extractor_version_used} "
        f"word_count={word_count} box_count={len(ocr_data.boxes) if ocr_data.boxes else 0} "
        f"labels={request.options.labels} image_size={image_width}x{image_height} "
        f"qaari_used={qaari_used} ocr_text_only={ocr_text_only} "
        f"corruption_detected={corruption_detected}"
    )
    
    # Convert to API response format
    entities: List[ExtractedEntity] = []
    entities_by_label = {}
    
    for entity_data in extracted_data:
        # Get snippet with context window
        snippet = _get_snippet(ocr_data.words, entity_data.token_indices, window=5)
        
        # Use bbox_norm_1000 from entity_data (already computed, or None if no bbox)
        bbox_norm_1000 = entity_data.bbox_norm_1000
        if bbox_norm_1000 is None and entity_data.bbox is not None:
            bbox_norm_1000 = normalize_bbox_to_1000(
                entity_data.bbox,
                image_width,
                image_height
            )
        
        # P12: Include span offsets if bbox is None
        entity_dict = {
            "label": entity_data.label,
            "value": entity_data.value,
            "confidence": entity_data.confidence,
            "source": {
                "ocr_engine": used_ocr_engine,
                "token_indices": entity_data.token_indices,
                "bbox": entity_data.bbox,
                "bbox_norm_1000": bbox_norm_1000,
                "span_start": entity_data.span_start,
                "span_end": entity_data.span_end,
            },
            "evidence": {
                "snippet": snippet,
                "page_no": page_no,
            },
        }
        
        # P19: Add low_confidence flag if present (LayoutXLM entities)
        if hasattr(entity_data, 'low_confidence') and entity_data.low_confidence is not None:
            entity_dict["low_confidence"] = entity_data.low_confidence
        
        entity = ExtractedEntity(**entity_dict)
        entities.append(entity)
        
        # Count by label
        label = entity.label
        entities_by_label[label] = entities_by_label.get(label, 0) + 1
    
    # Log extraction results with breakdown
    entities_by_label = {}
    for entity in entities:
        label = entity.label
        entities_by_label[label] = entities_by_label.get(label, 0) + 1
    
    logger.info(
        f"HF_EXTRACTOR_EXTRACT: doc_id={doc_id} page={page_no} "
        f"extractor_version_used={extractor_version_used} "
        f"entities_by_label={entities_by_label} "
        f"total_entities_count={len(entities)}"
    )
    
    
    # Build response
    extractor_info = ExtractorInfo(
        name="hf-extractor",
        model=MODEL_NAME,
        fine_tuned=False,
        version=EXTRACTOR_VERSION,
    )
    
    # P12: Compute needs_manual_review flag (include Qaari usage)
    needs_manual_review = (
        page_confidence < 0.40 or
        word_count < 8 or
        corruption_detected or
        qaari_used or
        ocr_text_only
    )
    
    quality = QualityMetrics(
        page_corrupted=False,
        page_ocr_confidence=page_confidence,
        ocr_engine_params=ocr_engine_params,
        ocr_used_fallback=ocr_used_fallback,
        extractor_version_used=extractor_version_used,
        model_loaded=model_loaded,
        model_name_or_path=model_name_or_path_used,
        needs_manual_review=needs_manual_review,
        corruption_detected=corruption_detected,
        qaari_used=qaari_used,
        ocr_text_only=ocr_text_only,
        qaari_model_name_or_path=qaari_model_name_or_path,
    )
    
    response = ExtractResponse(
        doc_id=doc_id,
        page_no=page_no,
        extractor=extractor_info,
        entities=entities,
        quality=quality,
    )
    
    return response


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8090,
        reload=False,
    )
