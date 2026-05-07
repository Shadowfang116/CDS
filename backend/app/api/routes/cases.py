import math
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentUser,
    require_approver,
    require_reviewer,
    require_tenant_scope,
    require_viewer,
)
from app.core.roles import role_satisfies
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.schemas.audit import AuditLogResponse
from app.schemas.case import CaseAssignmentUpdate, CaseCreate, CaseListResponse, CaseResponse, CaseStatusUpdate
from app.services.audit import log_request_event
from app.services.workflow import CASE_TRANSITIONS, normalize_case_status, transition_case

router = APIRouter(prefix="/cases", tags=["cases"])

ALLOWED_SORTS = {
    "created_at": Case.created_at,
    "updated_at": Case.updated_at,
    "status": Case.status,
    "title": Case.title,
}
DECISION_STATUSES = {"Approved", "Rejected"}


class CaseDecisionRequest(BaseModel):
    notes: str | None = None


def _get_case_or_404(db: Session, *, case_id: uuid.UUID, org_id: uuid.UUID) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _transition_case_with_audit(
    *,
    db: Session,
    request: Request,
    case: Case,
    current_user: CurrentUser,
    next_status: str,
    action: str,
) -> Case:
    normalized_status = normalize_case_status(next_status)
    if normalized_status not in CASE_TRANSITIONS:
        raise HTTPException(status_code=422, detail=f"Invalid status: {next_status}")
    if normalized_status in DECISION_STATUSES:
        raise HTTPException(
            status_code=403,
            detail="Use the approve or reject endpoints for decision transitions.",
        )

    before_snapshot = {
        "status": normalize_case_status(case.status),
        "decision": case.decision,
        "decided_at": case.decided_at.isoformat() if case.decided_at else None,
        "decided_by_user_id": str(case.decided_by_user_id) if case.decided_by_user_id else None,
        "decision_notes": case.decision_notes,
        "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
    }

    previous_status, current_status = transition_case(db, case=case, next_status=normalized_status)
    db.commit()
    db.refresh(case)

    log_request_event(
        db,
        request=request,
        action=action,
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        before_json=before_snapshot,
        after_json={
            "previous_status": previous_status,
            "status": current_status,
            "stored_status": case.status,
            "decision": case.decision,
            "decided_at": case.decided_at.isoformat() if case.decided_at else None,
            "decided_by_user_id": str(case.decided_by_user_id) if case.decided_by_user_id else None,
            "decision_notes": case.decision_notes,
            "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
        },
    )
    return case


def _ensure_case_transition_role(current_user: CurrentUser, *, next_status: str) -> None:
    normalized_status = normalize_case_status(next_status)
    if normalized_status == "Closed":
        if not role_satisfies(current_user.role, "Approver"):
            raise HTTPException(
                status_code=403,
                detail="Approver role is required to close a case.",
            )
        return

    if not role_satisfies(current_user.role, "Reviewer"):
        raise HTTPException(
            status_code=403,
            detail="Reviewer role is required to advance case workflow before approval.",
        )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    request: Request,
    case_data: CaseCreate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    case = Case(org_id=org_id, title=case_data.title, status="New")
    db.add(case)
    db.commit()
    db.refresh(case)

    log_request_event(
        db,
        request=request,
        action="case.create",
        org_id=org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        after_json={"title": case.title, "status": normalize_case_status(case.status)},
    )
    return case


@router.get("", response_model=CaseListResponse)
async def list_cases(
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search by case title"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort column"),
    order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
):
    _ = current_user
    base = db.query(Case).filter(Case.org_id == org_id)
    if q and q.strip():
        base = base.filter(Case.title.ilike(f"%{q.strip()}%"))

    total = base.with_entities(func.count(Case.id)).scalar() or 0
    sort_column = ALLOWED_SORTS.get(sort, Case.created_at)
    direction = sort_column.desc() if order == "desc" else sort_column.asc()
    items = base.order_by(direction).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, math.ceil(total / page_size)) if page_size else 1

    return CaseListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _ = current_user
    return _get_case_or_404(db, case_id=case_id, org_id=org_id)


@router.get("/{case_id}/audit", response_model=list[AuditLogResponse])
async def get_case_audit(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _ = current_user
    _get_case_or_404(db, case_id=case_id, org_id=org_id)
    return (
        db.query(AuditLog)
        .filter(AuditLog.org_id == org_id, AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )


@router.patch("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    request: Request,
    case_id: uuid.UUID,
    status_data: CaseStatusUpdate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _ensure_case_transition_role(current_user, next_status=status_data.status)
    case = _get_case_or_404(db, case_id=case_id, org_id=org_id)
    return _transition_case_with_audit(
        db=db,
        request=request,
        case=case,
        current_user=current_user,
        next_status=status_data.status,
        action="case.status_changed",
    )


@router.patch("/{case_id}/assignment", response_model=CaseResponse)
async def update_case_assignment(
    request: Request,
    case_id: uuid.UUID,
    assignment_data: CaseAssignmentUpdate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    if assignment_data.action not in {"claim", "unassign"}:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'claim' or 'unassign'.")

    case = _get_case_or_404(db, case_id=case_id, org_id=org_id)
    before_snapshot = {
        "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
    }
    case.assigned_to_user_id = current_user.user_id if assignment_data.action == "claim" else None
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    log_request_event(
        db,
        request=request,
        action="case.assignment_changed",
        org_id=org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        before_json=before_snapshot,
        after_json={
            "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
            "assignment_action": assignment_data.action,
        },
    )
    return case


@router.post("/{case_id}/approve", response_model=CaseResponse)
async def approve_case(
    request: Request,
    case_id: uuid.UUID,
    body: CaseDecisionRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_approver),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(db, case_id=case_id, org_id=org_id)
    before_snapshot = {
        "status": normalize_case_status(case.status),
        "decision": case.decision,
        "decided_at": case.decided_at.isoformat() if case.decided_at else None,
        "decided_by_user_id": str(case.decided_by_user_id) if case.decided_by_user_id else None,
        "decision_notes": case.decision_notes,
    }
    previous_status, current_status = transition_case(db, case=case, next_status="Approved")
    case.decision = "PASS"
    case.decided_at = datetime.utcnow()
    case.decided_by_user_id = current_user.user_id
    case.decision_notes = {"notes": body.notes} if body.notes else {}
    db.commit()
    db.refresh(case)

    log_request_event(
        db,
        request=request,
        action="case.approved",
        org_id=org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        before_json=before_snapshot,
        after_json={
            "previous_status": previous_status,
            "status": current_status,
            "decision": case.decision,
            "decided_at": case.decided_at.isoformat() if case.decided_at else None,
            "decided_by_user_id": str(case.decided_by_user_id),
            "decision_notes": case.decision_notes,
        },
    )
    return case


@router.post("/{case_id}/reject", response_model=CaseResponse)
async def reject_case(
    request: Request,
    case_id: uuid.UUID,
    body: CaseDecisionRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_approver),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(db, case_id=case_id, org_id=org_id)
    before_snapshot = {
        "status": normalize_case_status(case.status),
        "decision": case.decision,
        "decided_at": case.decided_at.isoformat() if case.decided_at else None,
        "decided_by_user_id": str(case.decided_by_user_id) if case.decided_by_user_id else None,
        "decision_notes": case.decision_notes,
    }
    previous_status, current_status = transition_case(db, case=case, next_status="Rejected")
    case.decision = "FAIL"
    case.decided_at = datetime.utcnow()
    case.decided_by_user_id = current_user.user_id
    case.decision_notes = {"notes": body.notes} if body.notes else {}
    db.commit()
    db.refresh(case)

    log_request_event(
        db,
        request=request,
        action="case.rejected",
        org_id=org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        before_json=before_snapshot,
        after_json={
            "previous_status": previous_status,
            "status": current_status,
            "decision": case.decision,
            "decided_at": case.decided_at.isoformat() if case.decided_at else None,
            "decided_by_user_id": str(case.decided_by_user_id),
            "decision_notes": case.decision_notes,
        },
    )
    return case
