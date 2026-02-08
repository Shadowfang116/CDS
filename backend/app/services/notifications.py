"""Notification service for in-app notifications."""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User, UserOrgRole


def create_notification(
    db: Session,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    case_id: Optional[uuid.UUID] = None,
) -> Notification:
    """
    Create a notification for a user or org.
    If user_id is None, it's an org-wide broadcast (all users can see it).
    """
    notification = Notification(
        org_id=org_id,
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notify_user(
    db: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    case_id: Optional[uuid.UUID] = None,
) -> Notification:
    """Create a notification for a specific user."""
    return create_notification(
        db=db,
        org_id=org_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
    )


def notify_role(
    db: Session,
    org_id: uuid.UUID,
    role: str,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    case_id: Optional[uuid.UUID] = None,
    exclude_user_id: Optional[uuid.UUID] = None,
) -> List[Notification]:
    """
    Fan-out notification to all users with a specific role in the org.
    Optionally exclude a specific user (e.g., the requester).
    """
    # Get all users with the specified role in this org
    role_mappings = db.query(UserOrgRole).filter(
        UserOrgRole.org_id == org_id,
        UserOrgRole.role == role,
    ).all()
    
    notifications = []
    for mapping in role_mappings:
        if exclude_user_id and mapping.user_id == exclude_user_id:
            continue
        
        notification = create_notification(
            db=db,
            org_id=org_id,
            user_id=mapping.user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            case_id=case_id,
        )
        notifications.append(notification)
    
    return notifications


def notify_approvers(
    db: Session,
    org_id: uuid.UUID,
    title: str,
    body: Optional[str] = None,
    severity: str = "info",
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    case_id: Optional[uuid.UUID] = None,
    exclude_user_id: Optional[uuid.UUID] = None,
) -> List[Notification]:
    """
    Notify all Approvers and Admins in the org about a new approval request.
    """
    notifications = []
    
    # Notify Approvers
    notifications.extend(notify_role(
        db=db,
        org_id=org_id,
        role="Approver",
        notification_type="approval_pending",
        title=title,
        body=body,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        exclude_user_id=exclude_user_id,
    ))
    
    # Also notify Admins
    notifications.extend(notify_role(
        db=db,
        org_id=org_id,
        role="Admin",
        notification_type="approval_pending",
        title=title,
        body=body,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        exclude_user_id=exclude_user_id,
    ))
    
    return notifications


def mark_notification_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
    """Mark a notification as read. Returns True if successful."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.org_id == org_id,
        Notification.user_id == user_id,
    ).first()
    
    if not notification:
        return False
    
    notification.is_read = True
    db.commit()
    return True


def mark_all_notifications_read(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> int:
    """Mark all notifications as read for a user. Returns count of updated notifications."""
    result = db.query(Notification).filter(
        Notification.org_id == org_id,
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return result


def get_unread_count(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> int:
    """Get count of unread notifications for a user."""
    return db.query(Notification).filter(
        Notification.org_id == org_id,
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()

