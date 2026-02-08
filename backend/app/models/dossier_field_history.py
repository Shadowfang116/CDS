"""Dossier field edit history model for audit trail."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class DossierFieldHistory(Base):
    """History of edits to dossier fields."""
    __tablename__ = "dossier_field_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    field_key = Column(String, nullable=False)  # e.g., "party.name", "property.plot_number"
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    edited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    edited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_type = Column(String, nullable=False)  # "manual" | "ocr_extraction_confirm" | "autofill"
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    source_page_number = Column(Integer, nullable=True)
    source_snippet = Column(JSONB, nullable=True)  # Selected OCR snippet evidence
    note = Column(Text, nullable=True)  # Optional note from editor
    
    __table_args__ = (
        Index("idx_dossier_field_history_org_case", "org_id", "case_id"),
        Index("idx_dossier_field_history_case_field", "case_id", "field_key"),
        Index("idx_dossier_field_history_edited_at", "edited_at"),
    )

