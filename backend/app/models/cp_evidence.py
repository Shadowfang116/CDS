"""CP Evidence Reference model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class CPEvidenceRef(Base):
    """Evidence references linking CPs to documents/pages."""
    __tablename__ = "cp_evidence_refs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    cp_id = Column(UUID(as_uuid=True), ForeignKey("cps.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    page_number = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    evidence_type = Column(String, nullable=True)  # "ocr_snippet" or None for regular evidence
    snippet_json = Column(JSONB, nullable=True)  # {document_id, page_number, snippet} for OCR snippets
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_cp_evidence_refs_org_cp", "org_id", "cp_id"),
    )

