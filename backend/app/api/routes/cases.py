import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseResponse, CaseStatusUpdate
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(prefix="/cases", tags=["cases"])

VALID_STATUSES = {
    "New",
    "Processing",
    "Review",
    "Pending Docs",
    "Ready for Approval",
    "Approved",
    "Rejected",
    "Closed",
}


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    request: Request,
    case_data: CaseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new case in the current user's org."""
    case = Case(
        org_id=current_user.org_id,
        title=case_data.title,
        status="New",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.create",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "title": case_data.title,
        },
    )
    
    return case


@router.get("", response_model=list[CaseResponse])
async def list_cases(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all cases for the current user's org (tenant isolation enforced)."""
    cases = db.query(Case).filter(Case.org_id == current_user.org_id).order_by(Case.created_at.desc()).all()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.list",
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "count": len(cases),
        },
    )
    
    return cases


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific case (tenant isolation enforced)."""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,  # Tenant isolation
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.view",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    
    return case


@router.patch("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    request: Request,
    case_id: uuid.UUID,
    status_data: CaseStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update case status (tenant isolation enforced)."""
    if status_data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,  # Tenant isolation
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    old_status = case.status
    case.status = status_data.status
    db.commit()
    db.refresh(case)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.status_change",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "old_status": old_status,
            "new_status": status_data.status,
        },
    )
    
    return case

