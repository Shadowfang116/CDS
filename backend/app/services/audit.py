import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
SYSTEM_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def _request_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def _stringify_entity_id(entity_id: Any) -> str | None:
    if entity_id is None:
        return None
    if isinstance(entity_id, uuid.UUID):
        return str(entity_id)
    return str(entity_id)


def _coerce_case_id(case_id: uuid.UUID | str | None) -> uuid.UUID | None:
    if case_id is None:
        return None
    if isinstance(case_id, uuid.UUID):
        return case_id
    try:
        return uuid.UUID(str(case_id))
    except (TypeError, ValueError):
        return None


def log_event(
    db: Session,
    *,
    action: str,
    org_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    entity_type: str | None = None,
    entity_id: Any = None,
    case_id: uuid.UUID | str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    before_snapshot: dict[str, Any] | None = None,
    after_snapshot: dict[str, Any] | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
    commit: bool = True,
) -> AuditLog:
    resolved_before_snapshot = before_snapshot if before_snapshot is not None else before_json
    resolved_after_snapshot = after_snapshot if after_snapshot is not None else after_json
    audit_entry = AuditLog(
        org_id=org_id or SYSTEM_ORG_ID,
        case_id=_coerce_case_id(case_id),
        actor_id=actor_id or SYSTEM_ACTOR_ID,
        action=action,
        entity_type=entity_type,
        entity_id=_stringify_entity_id(entity_id),
        before_json=resolved_before_snapshot,
        after_json=resolved_after_snapshot or {},
        ip_address=ip_address,
        request_id=request_id,
    )
    db.add(audit_entry)
    if commit:
        db.commit()
        db.refresh(audit_entry)
    else:
        db.flush()
    return audit_entry


def log_request_event(
    db: Session,
    *,
    request: Request | None,
    action: str,
    org_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    entity_type: str | None = None,
    entity_id: Any = None,
    case_id: uuid.UUID | str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    return log_event(
        db,
        action=action,
        org_id=org_id,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        before_json=before_json,
        after_json=after_json,
        ip_address=_request_ip(request),
        request_id=getattr(request.state, "request_id", None) if request else None,
        commit=commit,
    )


def write_audit_event(
    db: Session,
    org_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: Any = None,
    event_metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    case_id: uuid.UUID | str | None = None,
    ip_address: str | None = None,
    before_snapshot: dict[str, Any] | None = None,
    after_snapshot: dict[str, Any] | None = None,
):
    """Backward-compatible wrapper for legacy audit callsites."""
    return log_event(
        db,
        action=action,
        org_id=org_id,
        actor_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        after_json=event_metadata,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        ip_address=ip_address,
        request_id=request_id,
    )
