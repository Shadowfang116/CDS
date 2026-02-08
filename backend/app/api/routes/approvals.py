"""Approval workflow API routes."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.approval import ApprovalRequest, APPROVAL_REQUEST_TYPES
from app.models.case import Case
from app.models.user import User
from app.services.approvals import (
    create_approval_request,
    decide_approval_request,
    cancel_approval_request,
    get_case_readiness,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalRequestCreate(BaseModel):
    case_id: UUID
    request_type: str
    payload: Dict[str, Any]


class ApprovalDecision(BaseModel):
    reason: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    id: UUID
    case_id: UUID
    case_title: Optional[str] = None
    requested_by_user_id: UUID
    requested_by_email: Optional[str] = None
    requested_by_role: str
    request_type: str
    request_type_label: str
    status: str
    payload_json: Dict[str, Any]
    decided_by_user_id: Optional[UUID] = None
    decided_by_email: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApprovalListResponse(BaseModel):
    approvals: List[ApprovalRequestResponse]
    total: int


class CaseReadinessResponse(BaseModel):
    case_id: UUID
    ready: bool
    reasons: List[str]
    metrics: Dict[str, Any]


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    request: Request,
    status: Optional[str] = Query(default=None, description="Filter by status"),
    mine_only: bool = Query(default=False, description="Show only my requests"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List approval requests.
    - Approver/Admin: sees all pending org requests
    - Reviewer: sees only their own requests
    """
    query = db.query(ApprovalRequest).filter(
        ApprovalRequest.org_id == current_user.org_id
    )
    
    # Reviewers can only see their own requests
    if current_user.role == "Reviewer" or mine_only:
        query = query.filter(ApprovalRequest.requested_by_user_id == current_user.user_id)
    
    if status:
        query = query.filter(ApprovalRequest.status == status)
    
    total = query.count()
    approvals = query.order_by(ApprovalRequest.created_at.desc()).limit(limit).all()
    
    # Enrich with user emails and case titles
    user_ids = set()
    case_ids = set()
    for a in approvals:
        user_ids.add(a.requested_by_user_id)
        if a.decided_by_user_id:
            user_ids.add(a.decided_by_user_id)
        case_ids.add(a.case_id)
    
    users = {u.id: u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    cases = {c.id: c.title for c in db.query(Case).filter(Case.id.in_(case_ids)).all()}
    
    return ApprovalListResponse(
        approvals=[
            ApprovalRequestResponse(
                id=a.id,
                case_id=a.case_id,
                case_title=cases.get(a.case_id),
                requested_by_user_id=a.requested_by_user_id,
                requested_by_email=users.get(a.requested_by_user_id),
                requested_by_role=a.requested_by_role,
                request_type=a.request_type,
                request_type_label=APPROVAL_REQUEST_TYPES.get(a.request_type, a.request_type),
                status=a.status,
                payload_json=a.payload_json,
                decided_by_user_id=a.decided_by_user_id,
                decided_by_email=users.get(a.decided_by_user_id) if a.decided_by_user_id else None,
                decided_at=a.decided_at,
                decision_reason=a.decision_reason,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in approvals
        ],
        total=total,
    )


@router.post("", response_model=ApprovalRequestResponse, status_code=201)
async def create_approval(
    request: Request,
    payload: ApprovalRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new approval request (Maker action).
    Only Reviewer or Admin can create requests.
    """
    if current_user.role not in ["Reviewer", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Reviewer or Admin can create approval requests")
    
    approval = create_approval_request(
        db=db,
        org_id=current_user.org_id,
        case_id=payload.case_id,
        requested_by_user_id=current_user.user_id,
        requested_by_role=current_user.role,
        request_type=payload.request_type,
        payload=payload.payload,
    )
    
    # Get case title
    case = db.query(Case).filter(Case.id == payload.case_id).first()
    
    # Get requester email
    user = db.query(User).filter(User.id == current_user.user_id).first()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="approval.create",
        entity_type="approval",
        entity_id=approval.id,
        event_metadata={
            "request_type": approval.request_type,
            "case_id": str(approval.case_id),
            "payload": approval.payload_json,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="approval.pending",
        payload={
            "approval_id": str(approval.id),
            "case_id": str(approval.case_id),
            "case_title": case.title if case else None,
            "requested_by_email": user.email if user else None,
            "requested_by_role": approval.requested_by_role,
            "request_type": approval.request_type,
        },
    )
    
    return ApprovalRequestResponse(
        id=approval.id,
        case_id=approval.case_id,
        case_title=case.title if case else None,
        requested_by_user_id=approval.requested_by_user_id,
        requested_by_email=user.email if user else None,
        requested_by_role=approval.requested_by_role,
        request_type=approval.request_type,
        request_type_label=APPROVAL_REQUEST_TYPES.get(approval.request_type, approval.request_type),
        status=approval.status,
        payload_json=approval.payload_json,
        decided_by_user_id=approval.decided_by_user_id,
        decided_at=approval.decided_at,
        decision_reason=approval.decision_reason,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )


@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request: Request,
    approval_id: UUID,
    decision: ApprovalDecision,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Approve an approval request (Checker action).
    Only Approver or Admin can approve. Cannot approve own request.
    """
    if current_user.role not in ["Approver", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Approver or Admin can approve requests")
    
    approval = decide_approval_request(
        db=db,
        request_id=approval_id,
        decided_by_user_id=current_user.user_id,
        decided_by_role=current_user.role,
        org_id=current_user.org_id,
        approve=True,
        reason=decision.reason,
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="approval.approve",
        entity_type="approval",
        entity_id=approval.id,
        event_metadata={
            "request_type": approval.request_type,
            "reason": decision.reason,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    requester = db.query(User).filter(User.id == approval.requested_by_user_id).first()
    case = db.query(Case).filter(Case.id == approval.case_id).first()
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="approval.decided",
        payload={
            "approval_id": str(approval.id),
            "case_id": str(approval.case_id),
            "case_title": case.title if case else None,
            "requested_by_email": requester.email if requester else None,
            "request_type": approval.request_type,
            "decision": "approved",
            "reason": decision.reason,
        },
    )
    
    return _build_approval_response(db, approval)


@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request: Request,
    approval_id: UUID,
    decision: ApprovalDecision,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reject an approval request (Checker action).
    Only Approver or Admin can reject.
    """
    if current_user.role not in ["Approver", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Approver or Admin can reject requests")
    
    approval = decide_approval_request(
        db=db,
        request_id=approval_id,
        decided_by_user_id=current_user.user_id,
        decided_by_role=current_user.role,
        org_id=current_user.org_id,
        approve=False,
        reason=decision.reason,
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="approval.reject",
        entity_type="approval",
        entity_id=approval.id,
        event_metadata={
            "request_type": approval.request_type,
            "reason": decision.reason,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    requester = db.query(User).filter(User.id == approval.requested_by_user_id).first()
    case = db.query(Case).filter(Case.id == approval.case_id).first()
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="approval.decided",
        payload={
            "approval_id": str(approval.id),
            "case_id": str(approval.case_id),
            "case_title": case.title if case else None,
            "requested_by_email": requester.email if requester else None,
            "request_type": approval.request_type,
            "decision": "rejected",
            "reason": decision.reason,
        },
    )
    
    return _build_approval_response(db, approval)


@router.post("/{approval_id}/cancel", response_model=ApprovalRequestResponse)
async def cancel_request(
    request: Request,
    approval_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a pending approval request.
    Only the requester can cancel their own request.
    """
    approval = cancel_approval_request(
        db=db,
        request_id=approval_id,
        user_id=current_user.user_id,
        org_id=current_user.org_id,
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="approval.cancel",
        entity_type="approval",
        entity_id=approval.id,
        event_metadata={"request_type": approval.request_type},
    )
    
    return _build_approval_response(db, approval)


@router.get("/case/{case_id}/readiness", response_model=CaseReadinessResponse)
async def get_readiness(
    request: Request,
    case_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if a case is ready for final approval decision."""
    readiness = get_case_readiness(db, case_id, current_user.org_id)
    return CaseReadinessResponse(
        case_id=case_id,
        ready=readiness["ready"],
        reasons=readiness["reasons"],
        metrics=readiness["metrics"],
    )


def _build_approval_response(db: Session, approval: ApprovalRequest) -> ApprovalRequestResponse:
    """Helper to build approval response with enriched data."""
    case = db.query(Case).filter(Case.id == approval.case_id).first()
    requester = db.query(User).filter(User.id == approval.requested_by_user_id).first()
    decider = db.query(User).filter(User.id == approval.decided_by_user_id).first() if approval.decided_by_user_id else None
    
    return ApprovalRequestResponse(
        id=approval.id,
        case_id=approval.case_id,
        case_title=case.title if case else None,
        requested_by_user_id=approval.requested_by_user_id,
        requested_by_email=requester.email if requester else None,
        requested_by_role=approval.requested_by_role,
        request_type=approval.request_type,
        request_type_label=APPROVAL_REQUEST_TYPES.get(approval.request_type, approval.request_type),
        status=approval.status,
        payload_json=approval.payload_json,
        decided_by_user_id=approval.decided_by_user_id,
        decided_by_email=decider.email if decider else None,
        decided_at=approval.decided_at,
        decision_reason=approval.decision_reason,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )

