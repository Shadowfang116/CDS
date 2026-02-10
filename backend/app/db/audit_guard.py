"""Audit immutability: block UPDATE and DELETE on AuditLog. Only INSERT allowed."""
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


@event.listens_for(Session, "before_flush")
def _prevent_audit_mutation(session: Session, flush_context):
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise RuntimeError("[AUDIT] Deletion of audit logs is not allowed.")
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            if session.is_modified(obj, include_collections=False):
                raise RuntimeError("[AUDIT] Update of audit logs is not allowed.")
