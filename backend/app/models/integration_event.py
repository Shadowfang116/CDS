"""Integration event outbox model for async delivery."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class IntegrationEvent(Base):
    """Outbox table for integration events (email/webhooks)."""
    __tablename__ = "integration_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # approval.pending, approval.decided, case.decided, export.generated
    payload_json = Column(JSONB, nullable=False)
    
    # Processing state
    status = Column(String(20), nullable=False, default="Pending", index=True)  # Pending, Processing, Done, Failed
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    
    # Locking for concurrent processing
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(100), nullable=True)  # worker identifier
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_integration_events_org_status", "org_id", "status"),
        Index("idx_integration_events_next_attempt", "status", "next_attempt_at"),
    )

