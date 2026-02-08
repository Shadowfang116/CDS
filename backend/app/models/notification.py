"""Notification model for in-app notifications."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Notification(Base):
    """In-app notification for users."""
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null = broadcast to org
    
    type = Column(String(50), nullable=False)  # approval_pending, approval_decided, exception_high, etc.
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    
    # Entity references for deep linking
    entity_type = Column(String(50), nullable=True)  # case, exception, approval, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_notifications_user_unread", "user_id", "is_read", "created_at"),
        Index("idx_notifications_org_created", "org_id", "created_at"),
    )


class NotificationPreference(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    digest_opt_in = Column(Boolean, nullable=False, default=True)
    notify_on_approval = Column(Boolean, nullable=False, default=True)
    notify_on_high_risk = Column(Boolean, nullable=False, default=True)
    notify_on_case_update = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

