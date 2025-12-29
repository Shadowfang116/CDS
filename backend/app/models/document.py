import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, BigInteger, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    uploader_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    minio_key_original = Column(String, nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="Uploaded")  # Uploaded, Split, Failed
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_documents_org_case_created", "org_id", "case_id", "created_at"),
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)  # 1-based
    minio_key_page_pdf = Column(String, nullable=False)
    minio_key_thumbnail = Column(String, nullable=True)
    ocr_status = Column(String, nullable=False, default="NotStarted")  # NotStarted, Processing, Completed, Failed
    ocr_confidence = Column(Numeric, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_document_pages_org_doc_page", "org_id", "document_id", "page_number"),
    )

