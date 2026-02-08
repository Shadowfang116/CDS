"""OCR Extraction Candidates model for editable OCR extractions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Integer, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class OCRExtractionCandidate(Base):
    """OCR extraction candidate - pending/proposed/editable extractions before confirmation."""
    __tablename__ = "ocr_extraction_candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    field_key = Column(String, nullable=False)  # e.g. "party.name.raw", "property.plot_number"
    proposed_value = Column(Text, nullable=False)  # Value extracted by OCR/regex
    edited_value = Column(Text, nullable=True)  # Reviewer edits
    final_value = Column(Text, nullable=True)  # Value at confirm-time (computed = edited_value ?? proposed_value)
    status = Column(String, nullable=False, default="Pending")  # Pending | Confirmed | Rejected
    confidence = Column(Numeric, nullable=True)
    snippet = Column(Text, nullable=True)  # Short OCR snippet context
    confirmed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    rejected_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    amendment_of = Column(UUID(as_uuid=True), ForeignKey("ocr_extraction_candidates.id"), nullable=True)  # If this is an amendment
    # P10: Quality gate fields
    quality_level_at_create = Column(String, nullable=True)  # "Good" | "Low" | "Critical"
    is_low_quality = Column(Boolean, nullable=False, default=False)
    warning_reason = Column(Text, nullable=True)  # Reason for low quality flag
    # P15: Manual override fields (bank-ready audit trail)
    overridden_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    overridden_at = Column(DateTime, nullable=True)
    override_note = Column(Text, nullable=True)  # Reason/note for manual override
    # P16: HF Extractor fields
    extraction_method = Column(String, nullable=True)  # e.g., "hf_extractor", "heuristic", "manual"
    evidence_json = Column(JSONB, nullable=True)  # Structured evidence from AI extractors
    # P20: Run ID for deterministic per-run tracking
    run_id = Column(String(32), nullable=True, index=True)  # request_id from autofill_dossier
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_ocr_extractions_org_case_status", "org_id", "case_id", "status"),
        Index("idx_ocr_extractions_org_field", "org_id", "field_key"),
        Index("idx_ocr_extractions_extraction_method", "extraction_method"),
    )

