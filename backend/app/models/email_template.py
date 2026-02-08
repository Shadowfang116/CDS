"""Email template and delivery models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class EmailTemplate(Base):
    """Email template configuration per org."""
    __tablename__ = "email_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    template_key = Column(String(50), nullable=False, index=True)  # approval.pending, approval.decided, case.decided, export.generated
    subject = Column(String(200), nullable=False)
    body_md = Column(Text, nullable=False)  # Markdown body with {{var}} placeholders
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_email_templates_org_key", "org_id", "template_key", unique=True),
    )


class EmailDelivery(Base):
    """Email delivery attempt log."""
    __tablename__ = "email_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    to_email = Column(String(200), nullable=False, index=True)
    template_key = Column(String(50), nullable=False)
    subject = Column(String(200), nullable=False)
    
    # Delivery status
    status = Column(String(20), nullable=False, default="Pending", index=True)  # Pending, Success, Failed
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_email_deliveries_org_email", "org_id", "to_email", "created_at"),
        Index("idx_email_deliveries_status", "status", "created_at"),
    )

