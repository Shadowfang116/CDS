import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Index, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class OCRTextCorrection(Base):
    """OCR text corrections per document page (overlay, does not overwrite raw OCR)."""
    __tablename__ = "ocr_text_corrections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    corrected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)  # Strongly recommended but nullable for backward compatibility
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("org_id", "document_id", "page_number", name="uq_ocr_correction_org_doc_page"),
        Index("idx_ocr_corrections_org_doc", "org_id", "document_id"),
    )

