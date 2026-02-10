"""D5: Export registry model (Phase 8: status, error fields, request_id)."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

EXPORT_STATUS_PENDING = "pending"
EXPORT_STATUS_RUNNING = "running"
EXPORT_STATUS_SUCCEEDED = "succeeded"
EXPORT_STATUS_FAILED = "failed"

ERROR_MESSAGE_MAX_LENGTH = 1000


class Export(Base):
    """Export registry for generated DOCX and PDF files."""
    __tablename__ = "exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    export_type = Column(String, nullable=False)  # discrepancy_letter, undertaking_indemnity, internal_opinion, bank_pack_pdf
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    minio_key = Column(String, nullable=True)  # null until succeeded (storage path in MinIO)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Phase 8: lifecycle and failure surfacing
    status = Column(String, nullable=False, default=EXPORT_STATUS_SUCCEEDED)  # pending | running | succeeded | failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_code = Column(String, nullable=True)  # e.g. LO_TIMEOUT, GENERATION_ERROR
    error_message = Column(String(ERROR_MESSAGE_MAX_LENGTH), nullable=True)
    request_id = Column(String, nullable=True)  # correlation id from request

    __table_args__ = (
        Index("idx_exports_org_case_created", "org_id", "case_id", "created_at"),
        Index("idx_exports_org_case_type_status", "org_id", "case_id", "export_type", "status"),
    )

