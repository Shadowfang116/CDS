"""Case-level audit timeline API (append-only)."""
import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.user import User

router = APIRouter(tags=["audit"]) 


class AuditEvent(BaseModel):
    timestamp: str
    user_id: str
    user_name: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Dict[str, Any] = {}


class AuditTimelineResponse(BaseModel):
    case_id: str
    events: List[AuditEvent]


@router.get("/cases/{case_id}/audit", response_model=AuditTimelineResponse)
async def get_case_audit_timeline(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == current_user.org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    rows = db.query(AuditLog).filter(
        AuditLog.org_id == current_user.org_id,
        AuditLog.case_id == case_id,
    ).order_by(AuditLog.created_at.asc()).all()

    # optional name map
    user_ids = list({r.actor_user_id for r in rows if r.actor_user_id})
    name_map: Dict[str, str] = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids), User.org_id == current_user.org_id).all()
        for u in users:
            name_map[str(u.id)] = u.email or (u.name if hasattr(u, 'name') else None) or str(u.id)

    events: List[AuditEvent] = []
    for r in rows:
        uid = str(r.actor_user_id)
        events.append(AuditEvent(
            timestamp=r.created_at.isoformat(),
            user_id=uid,
            user_name=name_map.get(uid),
            action=r.action,
            entity_type=r.entity_type,
            entity_id=str(r.entity_id) if r.entity_id else None,
            details=r.event_metadata or {},
        ))

    return AuditTimelineResponse(case_id=str(case_id), events=events)

