"""Case-level audit timeline API."""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, require_tenant_scope, require_viewer
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.user import User, UserOrgRole
from app.schemas.audit import AuditLogResponse

router = APIRouter(tags=["audit"])


class AuditEvent(BaseModel):
    timestamp: str
    user_id: str
    user_name: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditTimelineResponse(BaseModel):
    case_id: str
    events: List[AuditEvent]


@router.get("/audit", response_model=list[AuditLogResponse])
async def list_global_audit_feed(
    limit: int = Query(default=100, ge=1, le=200),
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _ = current_user
    return (
        db.query(AuditLog)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/cases/{case_id}/audit", response_model=AuditTimelineResponse)
async def get_case_audit_timeline(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(UserOrgRole)
        .filter(
            UserOrgRole.user_id == current_user.user_id,
            UserOrgRole.org_id == current_user.org_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")

    case = db.query(Case).filter(Case.id == case_id, Case.org_id == current_user.org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.org_id == current_user.org_id,
            AuditLog.case_id == str(case_id),
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    user_ids = list({row.actor_user_id for row in rows if row.actor_user_id})
    name_map: Dict[str, str] = {}
    if user_ids:
        users = (
            db.query(User)
            .join(UserOrgRole, UserOrgRole.user_id == User.id)
            .filter(
                User.id.in_(user_ids),
                UserOrgRole.org_id == current_user.org_id,
            )
            .all()
        )
        for user in users:
            name_map[str(user.id)] = user.full_name or user.email or str(user.id)

    events = [
        AuditEvent(
            timestamp=row.created_at.isoformat(),
            user_id=str(row.actor_user_id),
            user_name=name_map.get(str(row.actor_user_id)),
            action=row.action,
            entity_type=row.entity_type,
            entity_id=str(row.entity_id) if row.entity_id else None,
            details={
                "metadata": row.event_metadata or {},
                "before_snapshot": row.before_snapshot,
                "after_snapshot": row.after_snapshot,
                "ip_address": row.ip_address,
                "request_id": row.request_id,
            },
        )
        for row in rows
    ]

    return AuditTimelineResponse(case_id=str(case_id), events=events)
