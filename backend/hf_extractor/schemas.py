"""Pydantic schemas for extraction API request/response."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Available entity labels
VALID_LABELS = ["CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT", "PERSON_NAME"]


class ImageData(BaseModel):
    """Image data with content type and base64 encoding."""
    content_type: str = Field(..., description="MIME type of the image")
    base64: str = Field(..., description="Base64-encoded image data")


class OCRData(BaseModel):
    """OCR result data."""
    engine: str = Field(..., description="OCR engine used: paddleocr|tesseract|qaari_vl")
    page_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall page OCR confidence")
    words: List[str] = Field(..., description="List of detected words")
    boxes: Optional[List[List[float]]] = Field(None, description="Bounding boxes: [[x1,y1,x2,y2], ...] (None for text-only OCR)")
    normalized: bool = Field(True, description="Whether boxes are normalized")


class ExtractOptions(BaseModel):
    """Extraction options."""
    extractor_version: Optional[str] = Field("rules-v1", description="Extractor version: 'rules-v1' or 'layoutxlm-v1'")
    return_token_spans: bool = Field(True, description="Whether to return token indices")
    language_hint: Optional[str] = Field("en", description="Language hint: ur|en|mixed")
    labels: Optional[List[str]] = Field(None, description="Optional list of labels to extract. If None, extracts all available labels.")
    # P17: OCR routing options
    min_ocr_confidence: Optional[float] = Field(0.55, description="Minimum OCR confidence to accept primary OCR (0.0-1.0)")
    enable_ocr_fallback: Optional[bool] = Field(True, description="Enable automatic OCR fallback if primary OCR confidence is low")
    force_ocr_fallback: Optional[bool] = Field(False, description="Force fallback OCR to run (for testing)")
    # P18: LayoutXLM options
    enable_layoutxlm: Optional[bool] = Field(False, description="Enable LayoutXLM model extraction (requires ML deps and model)")
    model_name_or_path: Optional[str] = Field(None, description="HuggingFace model path or name (overrides env HF_LAYOUTXLM_MODEL_PATH)")
    # P19: Confidence gates
    min_entity_confidence: Optional[float] = Field(0.60, description="Minimum entity confidence threshold (default: 0.60)")
    min_entity_confidence_cnic: Optional[float] = Field(0.70, description="Minimum CNIC entity confidence threshold (default: 0.70)")
    return_low_confidence: Optional[bool] = Field(False, description="Return entities below confidence threshold (flagged as low_confidence)")
    # P12: Qaari OCR options
    enable_qaari: Optional[bool] = Field(False, description="Enable Qaari OCR fallback for Urdu-heavy documents (requires VLM deps)")
    qaari_model_name_or_path: Optional[str] = Field(None, description="Qaari model path or name (overrides env HF_QAARI_MODEL_PATH)")


class ExtractRequest(BaseModel):
    """Request schema for POST /v1/extract."""
    doc_id: str = Field(..., description="Document UUID")
    page_no: int = Field(..., ge=1, description="Page number (1-indexed)")
    image: ImageData = Field(..., description="Image data (required)")
    ocr: Optional[OCRData] = Field(None, description="OCR results (optional; if missing, OCR will be run on image)")
    options: ExtractOptions = Field(..., description="Extraction options")


class ExtractorInfo(BaseModel):
    """Extractor metadata."""
    name: str = Field(..., description="Extractor name")
    model: str = Field(..., description="Model identifier")
    fine_tuned: bool = Field(False, description="Whether model is fine-tuned")
    version: str = Field(..., description="Extractor version")


class EntitySource(BaseModel):
    """Source information for extracted entity."""
    ocr_engine: str = Field(..., description="OCR engine that produced source tokens")
    token_indices: List[int] = Field(..., description="Indices into OCR words array")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [x1, y1, x2, y2] (None for text-only OCR)")
    bbox_norm_1000: Optional[List[int]] = Field(None, description="Normalized bbox [x1, y1, x2, y2] scaled to 0-1000 (None if no bbox)")
    span_start: Optional[int] = Field(None, description="Character offset start in page text (for text-only OCR)")
    span_end: Optional[int] = Field(None, description="Character offset end in page text (for text-only OCR)")


class EntityEvidence(BaseModel):
    """Evidence snippet for extracted entity."""
    snippet: str = Field(..., description="Text snippet from OCR (max 120 chars)")
    page_no: int = Field(..., description="Page number where evidence was found")


class ExtractedEntity(BaseModel):
    """A single extracted entity."""
    label: str = Field(..., description="Entity label: CNIC|PERSON_NAME|PLOT_NO|SCHEME_AUTHORITY|REGISTRY_NO|DATE|AMOUNT")
    value: str = Field(..., description="Extracted value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source: EntitySource = Field(..., description="Source information")
    evidence: EntityEvidence = Field(..., description="Evidence snippet")
    low_confidence: Optional[bool] = Field(None, description="P19: Flag indicating entity confidence is below threshold (LayoutXLM only)")


class QualityMetrics(BaseModel):
    """Page quality metrics."""
    page_corrupted: bool = Field(False, description="Whether page is corrupted")
    page_ocr_confidence: float = Field(..., ge=0.0, le=1.0, description="Page OCR confidence")
    # P17: OCR routing metadata (optional, for evidence persistence)
    ocr_engine_params: Optional[Dict[str, Any]] = Field(None, description="OCR engine parameters used (psm, oem, lang)")
    ocr_used_fallback: Optional[bool] = Field(None, description="Whether OCR fallback was used")
    # P18: LayoutXLM metadata
    extractor_version_used: Optional[str] = Field(None, description="Extractor version actually used ('rules-v1' or 'layoutxlm-v1')")
    model_loaded: Optional[bool] = Field(None, description="Whether LayoutXLM model was successfully loaded")
    model_name_or_path: Optional[str] = Field(None, description="LayoutXLM model name or path used")
    # P19: Quality flags
    needs_manual_review: Optional[bool] = Field(None, description="Flag indicating manual review may be needed (low OCR confidence, corruption, etc.)")
    corruption_detected: Optional[bool] = Field(None, description="Flag indicating corruption/mojibake was detected in OCR text")
    # P12: Qaari OCR metadata
    qaari_used: Optional[bool] = Field(None, description="Whether Qaari OCR was used")
    ocr_text_only: Optional[bool] = Field(None, description="Whether OCR result is text-only (no bounding boxes)")
    qaari_model_name_or_path: Optional[str] = Field(None, description="Qaari model name or path used")


class ExtractResponse(BaseModel):
    """Response schema for POST /v1/extract."""
    doc_id: str = Field(..., description="Document UUID")
    page_no: int = Field(..., description="Page number")
    extractor: ExtractorInfo = Field(..., description="Extractor metadata")
    entities: List[ExtractedEntity] = Field(default_factory=list, description="List of extracted entities")
    quality: QualityMetrics = Field(..., description="Quality metrics")


class HealthResponse(BaseModel):
    """Response schema for GET /health."""
    ok: bool = Field(True, description="Service health status")

