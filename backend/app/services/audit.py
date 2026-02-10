import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def write_audit_event(
    db: Session,
    org_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    event_metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
):
    """Append-only audit log writer. request_id should come from request.state.request_id when in HTTP context."""
    audit_entry = AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=event_metadata or {},
        request_id=request_id,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

