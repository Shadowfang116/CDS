"""Email templates management API (Admin only)."""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser, require_role, require_tenant_scope
from app.services.audit import write_audit_event
from app.models.email_template import EmailTemplate, EmailDelivery
from app.services.event_bus import emit_event

router = APIRouter(prefix="/integrations/email", tags=["integrations"])


class EmailTemplateCreate(BaseModel):
    template_key: str
    subject: str
    body_md: str
    is_enabled: bool = True


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body_md: Optional[str] = None
    is_enabled: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    id: uuid.UUID
    template_key: str
    subject: str
    body_md: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class EmailDeliveryResponse(BaseModel):
    id: uuid.UUID
    to_email: str
    template_key: str
    subject: str
    status: str
    attempt_count: int
    last_error: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]


VALID_TEMPLATE_KEYS = ["approval.pending", "approval.decided", "case.decided", "export.generated"]


@router.get("/templates", response_model=List[EmailTemplateResponse])
async def list_templates(
    request: Request,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """List all email templates for the org (Admin only)."""
    templates = db.query(EmailTemplate).filter(
        EmailTemplate.org_id == org_id
    ).order_by(EmailTemplate.template_key).all()
    
    return [
        EmailTemplateResponse(
            id=t.id,
            template_key=t.template_key,
            subject=t.subject,
            body_md=t.body_md,
            is_enabled=t.is_enabled,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.post("/templates", response_model=EmailTemplateResponse, status_code=201)
async def create_template(
    request: Request,
    payload: EmailTemplateCreate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Create an email template (Admin only)."""
    if payload.template_key not in VALID_TEMPLATE_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid template_key. Must be one of: {VALID_TEMPLATE_KEYS}")
    
    existing = db.query(EmailTemplate).filter(
        EmailTemplate.org_id == org_id,
        EmailTemplate.template_key == payload.template_key,
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Template for {payload.template_key} already exists")
    
    template = EmailTemplate(
        org_id=org_id,
        template_key=payload.template_key,
        subject=payload.subject,
        body_md=payload.body_md,
        is_enabled=payload.is_enabled,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.email.template_create",
        entity_type="email_template",
        entity_id=template.id,
        event_metadata={"template_key": template.template_key},
    )
    
    return EmailTemplateResponse(
        id=template.id,
        template_key=template.template_key,
        subject=template.subject,
        body_md=template.body_md,
        is_enabled=template.is_enabled,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.patch("/templates/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    request: Request,
    template_id: uuid.UUID,
    payload: EmailTemplateUpdate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Update an email template (Admin only)."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.org_id == org_id,
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    if payload.subject is not None:
        template.subject = payload.subject
    if payload.body_md is not None:
        template.body_md = payload.body_md
    if payload.is_enabled is not None:
        template.is_enabled = payload.is_enabled
    
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.email.template_update",
        entity_type="email_template",
        entity_id=template.id,
        event_metadata={"template_key": template.template_key},
    )
    
    return EmailTemplateResponse(
        id=template.id,
        template_key=template.template_key,
        subject=template.subject,
        body_md=template.body_md,
        is_enabled=template.is_enabled,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/deliveries", response_model=List[EmailDeliveryResponse])
async def list_deliveries(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """List email deliveries for the org (Admin only)."""
    deliveries = db.query(EmailDelivery).filter(
        EmailDelivery.org_id == org_id
    ).order_by(EmailDelivery.created_at.desc()).limit(limit).all()
    
    return [
        EmailDeliveryResponse(
            id=d.id,
            to_email=d.to_email,
            template_key=d.template_key,
            subject=d.subject,
            status=d.status,
            attempt_count=d.attempt_count,
            last_error=d.last_error,
            created_at=d.created_at,
            sent_at=d.sent_at,
        )
        for d in deliveries
    ]


@router.post("/test", status_code=200)
async def test_email(
    request: Request,
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Send a test email to the current user's email (Admin only)."""
    from app.models.user import User
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user or not user.email:
        raise HTTPException(status_code=400, detail="User email not found")
    
    # Emit test event
    test_event = emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",
        payload={
            "test": True,
            "to_email": user.email,
            "export_type": "test",
            "filename": "test.pdf",
            "case_title": "Test Case",
            "case_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.email.test",
        entity_type="email_template",
        entity_id=None,
        event_metadata={"to_email": user.email, "event_id": str(test_event.id)},
    )
    
    return {"message": "Test email event emitted", "event_id": str(test_event.id), "to_email": user.email}

