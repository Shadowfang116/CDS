"""Rules API endpoints - Evaluate, Exceptions, CPs."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case import Case
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.rule_engine import run_rules

router = APIRouter(tags=["rules"])


# ============================================================
# SCHEMAS
# ============================================================

class EvaluateResponse(BaseModel):
    case_id: str
    high: int
    medium: int
    low: int
    total: int
    cps_total: int


class EvidenceRefResponse(BaseModel):
    id: str
    document_id: Optional[str]
    page_number: Optional[int]
    note: Optional[str]
    
    class Config:
        from_attributes = True


class ExceptionResponse(BaseModel):
    id: str
    rule_id: str
    module: str
    severity: str
    title: str
    description: Optional[str]
    cp_text: Optional[str]
    resolution_conditions: Optional[str]
    status: str
    waiver_reason: Optional[str]
    resolved_by_user_id: Optional[str]
    resolved_at: Optional[datetime]
    waived_by_user_id: Optional[str]
    waived_at: Optional[datetime]
    created_at: datetime
    evidence_refs: List[EvidenceRefResponse] = []
    
    class Config:
        from_attributes = True


class ExceptionsListResponse(BaseModel):
    case_id: str
    total: int
    high_count: int
    medium_count: int
    low_count: int
    open_count: int
    resolved_count: int
    waived_count: int
    exceptions: List[ExceptionResponse]


class CPResponse(BaseModel):
    id: str
    rule_id: str
    severity: str
    text: str
    evidence_required: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CPsListResponse(BaseModel):
    case_id: str
    total: int
    open_count: int
    satisfied_count: int
    waived_count: int
    cps: List[CPResponse]


class ExceptionActionRequest(BaseModel):
    action: str  # "resolve" or "waive"
    reason: Optional[str] = None  # Required for waive


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/cases/{case_id}/evaluate", response_model=EvaluateResponse)
async def evaluate_case(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run rule engine on a case, creating exceptions and CPs."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Run rules
    counts = run_rules(db, current_user.org_id, case_id, current_user.user_id)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="rules.evaluate",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            **counts,
        },
    )
    
    return EvaluateResponse(
        case_id=str(case_id),
        **counts,
    )


@router.get("/cases/{case_id}/exceptions", response_model=ExceptionsListResponse)
async def list_exceptions(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all exceptions for a case with evidence references."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get exceptions
    exceptions = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == current_user.org_id,
    ).order_by(
        Exception_.severity.desc(),
        Exception_.created_at.desc(),
    ).all()
    
    # Get evidence refs for all exceptions
    exception_ids = [e.id for e in exceptions]
    evidence_refs = db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.exception_id.in_(exception_ids),
        ExceptionEvidenceRef.org_id == current_user.org_id,
    ).all()
    
    # Group evidence by exception
    evidence_by_exception = {}
    for ref in evidence_refs:
        if ref.exception_id not in evidence_by_exception:
            evidence_by_exception[ref.exception_id] = []
        evidence_by_exception[ref.exception_id].append(ref)
    
    # Build response
    exception_responses = []
    for exc in exceptions:
        refs = evidence_by_exception.get(exc.id, [])
        exception_responses.append(ExceptionResponse(
            id=str(exc.id),
            rule_id=exc.rule_id,
            module=exc.module,
            severity=exc.severity,
            title=exc.title,
            description=exc.description,
            cp_text=exc.cp_text,
            resolution_conditions=exc.resolution_conditions,
            status=exc.status,
            waiver_reason=exc.waiver_reason,
            resolved_by_user_id=str(exc.resolved_by_user_id) if exc.resolved_by_user_id else None,
            resolved_at=exc.resolved_at,
            waived_by_user_id=str(exc.waived_by_user_id) if exc.waived_by_user_id else None,
            waived_at=exc.waived_at,
            created_at=exc.created_at,
            evidence_refs=[
                EvidenceRefResponse(
                    id=str(r.id),
                    document_id=str(r.document_id) if r.document_id else None,
                    page_number=r.page_number,
                    note=r.note,
                )
                for r in refs
            ],
        ))
    
    # Calculate counts
    high_count = sum(1 for e in exceptions if e.severity == "High")
    medium_count = sum(1 for e in exceptions if e.severity == "Medium")
    low_count = sum(1 for e in exceptions if e.severity == "Low")
    open_count = sum(1 for e in exceptions if e.status == "Open")
    resolved_count = sum(1 for e in exceptions if e.status == "Resolved")
    waived_count = sum(1 for e in exceptions if e.status == "Waived")
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="exceptions.list",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "count": len(exceptions),
        },
    )
    
    return ExceptionsListResponse(
        case_id=str(case_id),
        total=len(exceptions),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        open_count=open_count,
        resolved_count=resolved_count,
        waived_count=waived_count,
        exceptions=exception_responses,
    )


@router.get("/cases/{case_id}/cps", response_model=CPsListResponse)
async def list_cps(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all Conditions Precedent for a case."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get CPs
    cps = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == current_user.org_id,
    ).order_by(
        ConditionPrecedent.severity.desc(),
        ConditionPrecedent.created_at.desc(),
    ).all()
    
    # Build response
    cp_responses = [
        CPResponse(
            id=str(cp.id),
            rule_id=cp.rule_id,
            severity=cp.severity,
            text=cp.text,
            evidence_required=cp.evidence_required,
            status=cp.status,
            created_at=cp.created_at,
        )
        for cp in cps
    ]
    
    # Calculate counts
    open_count = sum(1 for c in cps if c.status == "Open")
    satisfied_count = sum(1 for c in cps if c.status == "Satisfied")
    waived_count = sum(1 for c in cps if c.status == "Waived")
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="cps.list",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "count": len(cps),
        },
    )
    
    return CPsListResponse(
        case_id=str(case_id),
        total=len(cps),
        open_count=open_count,
        satisfied_count=satisfied_count,
        waived_count=waived_count,
        cps=cp_responses,
    )


@router.get("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def get_exception(
    request: Request,
    exception_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single exception with evidence references."""
    exc = db.query(Exception_).filter(
        Exception_.id == exception_id,
        Exception_.org_id == current_user.org_id,
    ).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    # Get evidence refs
    evidence_refs = db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.exception_id == exception_id,
        ExceptionEvidenceRef.org_id == current_user.org_id,
    ).all()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="exception.view",
        entity_type="exception",
        entity_id=exception_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "exception_id": str(exception_id),
            "case_id": str(exc.case_id),
        },
    )
    
    return ExceptionResponse(
        id=str(exc.id),
        rule_id=exc.rule_id,
        module=exc.module,
        severity=exc.severity,
        title=exc.title,
        description=exc.description,
        cp_text=exc.cp_text,
        resolution_conditions=exc.resolution_conditions,
        status=exc.status,
        waiver_reason=exc.waiver_reason,
        resolved_by_user_id=str(exc.resolved_by_user_id) if exc.resolved_by_user_id else None,
        resolved_at=exc.resolved_at,
        waived_by_user_id=str(exc.waived_by_user_id) if exc.waived_by_user_id else None,
        waived_at=exc.waived_at,
        created_at=exc.created_at,
        evidence_refs=[
            EvidenceRefResponse(
                id=str(r.id),
                document_id=str(r.document_id) if r.document_id else None,
                page_number=r.page_number,
                note=r.note,
            )
            for r in evidence_refs
        ],
    )


@router.patch("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def update_exception(
    request: Request,
    exception_id: uuid.UUID,
    body: ExceptionActionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve or waive an exception. Waive requires Approver role."""
    exc = db.query(Exception_).filter(
        Exception_.id == exception_id,
        Exception_.org_id == current_user.org_id,
    ).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    if exc.status != "Open":
        raise HTTPException(status_code=400, detail=f"Exception is already {exc.status}")
    
    action = body.action.lower()
    
    if action == "resolve":
        # Reviewer+ can resolve
        if current_user.role not in ["Admin", "Approver", "Reviewer"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to resolve")
        
        exc.status = "Resolved"
        exc.resolved_by_user_id = current_user.user_id
        exc.resolved_at = datetime.utcnow()
        
        audit_action = "exception.resolve"
        
    elif action == "waive":
        # Only Approver+ can waive
        if current_user.role not in ["Admin", "Approver"]:
            raise HTTPException(status_code=403, detail="Only Approver or Admin can waive exceptions")
        
        if not body.reason:
            raise HTTPException(status_code=400, detail="Waiver reason is required")
        
        exc.status = "Waived"
        exc.waiver_reason = body.reason
        exc.waived_by_user_id = current_user.user_id
        exc.waived_at = datetime.utcnow()
        
        audit_action = "exception.waive"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    db.commit()
    db.refresh(exc)
    
    # Get evidence refs
    evidence_refs = db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.exception_id == exception_id,
        ExceptionEvidenceRef.org_id == current_user.org_id,
    ).all()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action=audit_action,
        entity_type="exception",
        entity_id=exception_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "exception_id": str(exception_id),
            "case_id": str(exc.case_id),
            "action": action,
            "reason": body.reason,
        },
    )
    
    return ExceptionResponse(
        id=str(exc.id),
        rule_id=exc.rule_id,
        module=exc.module,
        severity=exc.severity,
        title=exc.title,
        description=exc.description,
        cp_text=exc.cp_text,
        resolution_conditions=exc.resolution_conditions,
        status=exc.status,
        waiver_reason=exc.waiver_reason,
        resolved_by_user_id=str(exc.resolved_by_user_id) if exc.resolved_by_user_id else None,
        resolved_at=exc.resolved_at,
        waived_by_user_id=str(exc.waived_by_user_id) if exc.waived_by_user_id else None,
        waived_at=exc.waived_at,
        created_at=exc.created_at,
        evidence_refs=[
            EvidenceRefResponse(
                id=str(r.id),
                document_id=str(r.document_id) if r.document_id else None,
                page_number=r.page_number,
                note=r.note,
            )
            for r in evidence_refs
        ],
    )

