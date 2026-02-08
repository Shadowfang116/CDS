"""Saved dashboard views for quick filter access."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class SavedView(Base):
    """Saved dashboard filter views with sharing capabilities."""
    __tablename__ = "saved_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(60), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    config_json = Column(JSONB, nullable=False)  # {days: 30, severity: "High"|null, status: "Review"|null}
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Sharing fields (Phase 7)
    visibility = Column(String(20), nullable=False, default="private")  # "private" | "org"
    shared_with_roles = Column(JSONB, nullable=False, default=[])  # ["Admin", "Reviewer"] or [] for all
    shared_with_user_ids = Column(JSONB, nullable=False, default=[])  # [uuid, ...] for specific users
    last_used_at = Column(DateTime, nullable=True)  # Track usage for analytics
    
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_saved_views_org_name"),
        Index("idx_saved_views_org_default", "org_id", "is_default"),
        Index("idx_saved_views_org_visibility", "org_id", "visibility"),
    )

