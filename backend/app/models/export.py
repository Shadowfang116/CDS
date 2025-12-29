"""D5: Export registry model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Export(Base):
    """Export registry for generated DOCX and PDF files."""
    __tablename__ = "exports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    export_type = Column(String, nullable=False)  # discrepancy_letter, undertaking_indemnity, internal_opinion, bank_pack_pdf
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    minio_key = Column(String, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_exports_org_case_created", "org_id", "case_id", "created_at"),
    )

