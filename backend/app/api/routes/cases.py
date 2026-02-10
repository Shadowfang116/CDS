import math
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseListResponse, CaseResponse, CaseStatusUpdate
from app.api.deps import get_current_user, CurrentUser, require_tenant_scope, require_role
from app.services.audit import write_audit_event

router = APIRouter(prefix="/cases", tags=["cases"])

ALLOWED_SORTS = {
    "created_at": Case.created_at,
    "updated_at": Case.updated_at,
    "status": Case.status,
    "title": Case.title,
}

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
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin", "Approver", "Reviewer")),
    db: Session = Depends(get_db),
):
    """Create a new case in the current user's org (Admin/Approver/Reviewer)."""
    case = Case(
        org_id=org_id,
        title=case_data.title,
        status="New",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="case.create",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "title": case_data.title,
        },
        request_id=request_id,
    )
    
    return case


@router.get("", response_model=CaseListResponse)
async def list_cases(
    request: Request,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search by case title"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort column"),
    order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
):
    """List cases for the current user's org with pagination, search, and sort (tenant isolation enforced)."""
    base = db.query(Case).filter(Case.org_id == org_id)
    if q and q.strip():
        term = f"%{q.strip()}%"
        base = base.filter(Case.title.ilike(term))
    total = base.with_entities(func.count(Case.id)).scalar() or 0
    sort_column = ALLOWED_SORTS.get(sort, Case.created_at)
    direction = sort_column.desc() if order == "desc" else sort_column.asc()
    offset = (page - 1) * page_size
    cases = (
        base.order_by(direction)
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total_pages = max(1, math.ceil(total / page_size)) if page_size else 1

    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.list",
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "count": len(cases),
            "page": page,
            "total": total,
        },
        request_id=request_id,
    )

    return CaseListResponse(
        items=cases,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    request: Request,
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific case (tenant isolation: 404 if not in org)."""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.view",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
        request_id=request_id,
    )
    
    return case


@router.patch("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    request: Request,
    case_id: uuid.UUID,
    status_data: CaseStatusUpdate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin", "Approver", "Reviewer")),
    db: Session = Depends(get_db),
):
    """Update case status (tenant isolation: 404 if not in org)."""
    if status_data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    old_status = case.status
    case.status = status_data.status
    db.commit()
    db.refresh(case)
    
    request_id = getattr(request.state, "request_id", None)
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.status_change",
        entity_type="case",
        entity_id=case.id,
        event_metadata={
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "old_status": old_status,
            "new_status": status_data.status,
        },
        request_id=request_id,
    )
    
    return case

