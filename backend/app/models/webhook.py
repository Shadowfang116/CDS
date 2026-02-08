"""Webhook endpoint and delivery models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class WebhookEndpoint(Base):
    """Webhook endpoint configuration."""
    __tablename__ = "webhook_endpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    
    # Encrypted secret (never store plaintext)
    secret_ciphertext = Column(Text, nullable=False)
    secret_preview = Column(String(10), nullable=False)  # last 4 chars for display
    
    # Subscribed events (JSON array of event types)
    subscribed_events = Column(JSONB, nullable=False, default=list)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_webhook_endpoints_org_enabled", "org_id", "is_enabled"),
    )


class WebhookDelivery(Base):
    """Webhook delivery attempt log."""
    __tablename__ = "webhook_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint_id = Column(UUID(as_uuid=True), ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    payload_json = Column(JSONB, nullable=False)
    
    # Delivery status
    status = Column(String(20), nullable=False, default="Pending", index=True)  # Pending, Success, Failed
    attempt_count = Column(Integer, nullable=False, default=0)
    http_status = Column(Integer, nullable=True)
    response_body_snippet = Column(Text, nullable=True)  # First 500 chars of response
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_webhook_deliveries_org_endpoint", "org_id", "endpoint_id", "created_at"),
        Index("idx_webhook_deliveries_status", "status", "created_at"),
    )

