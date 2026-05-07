from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.rules import Exception_

STATUS_ALIASES = {
    "Pending Docs": "PendingDocs",
    "Ready for Approval": "ReadyForApproval",
}

STORAGE_STATUS = {
    "PendingDocs": "Pending Docs",
    "ReadyForApproval": "Ready for Approval",
}

CASE_TRANSITIONS = {
    "New": {"Processing"},
    "Processing": {"Review"},
    "Review": {"PendingDocs", "ReadyForApproval"},
    "PendingDocs": set(),
    "ReadyForApproval": {"Approved", "Rejected"},
    "Approved": {"Closed"},
    "Rejected": {"Closed"},
    "Closed": set(),
}

TERMINAL_CASE_STATUSES = {"Approved", "Rejected", "Closed"}


def normalize_case_status(value: str) -> str:
    cleaned = value.strip()
    return STATUS_ALIASES.get(cleaned, cleaned)


def storage_case_status(value: str) -> str:
    normalized = normalize_case_status(value)
    return STORAGE_STATUS.get(normalized, normalized)


def validate_case_transition(
    db: Session,
    *,
    case: Case,
    next_status: str,
) -> None:
    current_status = normalize_case_status(case.status)
    requested_status = normalize_case_status(next_status)
    allowed = CASE_TRANSITIONS.get(current_status, set())
    if requested_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid case status transition: {current_status} -> {requested_status}",
        )

    if requested_status == "Approved":
        open_critical = (
            db.query(Exception_)
            .filter(
                Exception_.case_id == case.id,
                Exception_.org_id == case.org_id,
                Exception_.severity == "Critical",
                Exception_.status == "Open",
            )
            .count()
        )
        if open_critical > 0:
            raise HTTPException(
                status_code=422,
                detail="Case cannot be approved while open critical exceptions remain.",
            )


def transition_case(
    db: Session,
    *,
    case: Case,
    next_status: str,
) -> tuple[str, str]:
    previous_status = normalize_case_status(case.status)
    requested_status = normalize_case_status(next_status)
    validate_case_transition(db, case=case, next_status=requested_status)
    case.status = storage_case_status(requested_status)
    case.updated_at = datetime.utcnow()
    return previous_status, requested_status


def can_generate_export(*, case_status: str, role: str) -> bool:
    return role == "Approver" and normalize_case_status(case_status) in TERMINAL_CASE_STATUSES


def audit_case_id_for_entity(
    *,
    case_id: uuid.UUID | None = None,
    case: Case | None = None,
) -> uuid.UUID | None:
    if case_id is not None:
        return case_id
    if case is not None:
        return case.id
    return None
