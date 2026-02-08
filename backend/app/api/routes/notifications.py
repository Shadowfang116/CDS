"""Notification API routes."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.notification import Notification
from app.services.notifications import mark_notification_read, mark_all_notifications_read, get_unread_count

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    body: Optional[str]
    severity: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    case_id: Optional[UUID]
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total: int


class MarkReadResponse(BaseModel):
    success: bool
    message: str


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    request: Request,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    query = db.query(Notification).filter(
        Notification.org_id == current_user.org_id,
        Notification.user_id == current_user.user_id,
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    unread_count = get_unread_count(db, current_user.user_id, current_user.org_id)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="notification.list",
        entity_type="notification",
        event_metadata={"unread_only": unread_only, "limit": limit},
    )
    
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                type=n.type,
                title=n.title,
                body=n.body,
                severity=n.severity,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                case_id=n.case_id,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=total,
    )


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_read(
    request: Request,
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    success = mark_notification_read(db, notification_id, current_user.user_id, current_user.org_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="notification.read",
        entity_type="notification",
        entity_id=notification_id,
    )
    
    return MarkReadResponse(success=True, message="Notification marked as read")


@router.post("/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    count = mark_all_notifications_read(db, current_user.user_id, current_user.org_id)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="notification.read_all",
        entity_type="notification",
        event_metadata={"count": count},
    )
    
    return MarkReadResponse(success=True, message=f"Marked {count} notifications as read")


@router.get("/unread-count")
async def get_unread_notification_count(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the count of unread notifications."""
    count = get_unread_count(db, current_user.user_id, current_user.org_id)
    return {"unread_count": count}

