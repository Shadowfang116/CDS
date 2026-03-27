"""Phase 10: OCR review, override, and rerun endpoints for document pages."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.case import Case
from app.models.document import Document, DocumentPage
from app.api.deps import get_current_user, CurrentUser, require_role, require_tenant_scope
from app.services.audit import write_audit_event
from app.services.storage import get_presigned_get_url
from app.services.page_text import get_effective_page_text

router = APIRouter(tags=["pages"])

DOWNLOAD_URL_EXPIRES_SECONDS = 3600


# ============================================================
# SCHEMAS
# ============================================================

class OcrReviewResponse(BaseModel):
    """Response for OCR review endpoint."""
    page_id: str
    page_number: int
    image_url: str
    ocr: dict
    meta: dict


class OcrOverrideRequest(BaseModel):
    """Request body for setting OCR override."""
    override_text: str
    reason: Optional[str] = None


class OcrRerunRequest(BaseModel):
    """Request body for re-running OCR."""
    force_profile: Optional[str] = None  # "basic"|"enhanced"
    force_detect: Optional[bool] = None
    force_lang: Optional[str] = None  # "urd"|"urd+eng"|"eng"
    force_layout: Optional[bool] = None
    force_pdf_text_layer: Optional[bool] = None
    engine_mode: Optional[str] = None  # "tesseract"|"ensemble"


class OcrRerunResponse(BaseModel):
    """Response for OCR rerun endpoint."""
    queued: bool
    page_id: str
    page_number: int
    task: str


# ============================================================
# GET OCR REVIEW
# ============================================================

@router.get(
    "/cases/{case_id}/documents/{document_id}/pages/{page_number}/ocr",
    response_model=OcrReviewResponse
)
async def get_page_ocr_review(
    request: Request,
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get OCR review payload for a page: image URL, effective text, metadata.
    
    Tenant-scoped: requires case, document, and page to belong to org_id.
    """
    # Load Case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Load Document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Load Page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
        DocumentPage.org_id == org_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Get effective text
    effective = get_effective_page_text(page)
    
    # Get image URL (use thumbnail if available, else page PDF)
    image_key = page.minio_key_thumbnail or page.minio_key_page_pdf
    image_url = get_presigned_get_url(image_key, DOWNLOAD_URL_EXPIRES_SECONDS)
    
    # Get OCR metadata (or empty dict)
    ocr_meta = page.ocr_meta if hasattr(page, 'ocr_meta') and page.ocr_meta else {}
    
    return OcrReviewResponse(
        page_id=str(page.id),
        page_number=page.page_number,
        image_url=image_url,
        ocr={
            "text": effective["text"],
            "source": effective["source"],
            "confidence": effective["confidence"],
            "has_override": effective["has_override"],
            "override": effective["override"],
        },
        meta=ocr_meta,
    )


# ============================================================
# PATCH OCR OVERRIDE
# ============================================================

@router.patch(
    "/cases/{case_id}/documents/{document_id}/pages/{page_number}/ocr",
    status_code=status.HTTP_200_OK
)
async def set_page_ocr_override(
    request: Request,
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    body: OcrOverrideRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin", "Approver", "Reviewer")),
    db: Session = Depends(get_db),
):
    """
    Set or update OCR override text for a page.
    
    Requires Admin, Approver, or Reviewer role.
    Tenant-scoped.
    """
    # Load Case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Load Document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Load Page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
        DocumentPage.org_id == org_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Validate override text
    if not body.override_text or not body.override_text.strip():
        raise HTTPException(status_code=400, detail="override_text cannot be empty")
    
    if len(body.override_text) > settings.OCR_TEXT_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"override_text exceeds maximum length of {settings.OCR_TEXT_MAX_LEN}"
        )
    
    # Set override
    page.ocr_text_override = body.override_text.strip()
    page.ocr_override_updated_at = datetime.utcnow()
    page.ocr_override_user_id = current_user.user_id
    page.ocr_override_reason = body.reason[:500] if body.reason else None
    
    db.commit()
    db.refresh(page)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.override_set",
        entity_type="document_page",
        entity_id=page.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "document_id": str(document_id),
            "page_number": page_number,
            "page_id": str(page.id),
            "override_len": len(body.override_text),
            "reason": body.reason,
        },
    )
    
    return {"message": "Override set successfully", "page_id": str(page.id)}


# ============================================================
# DELETE OCR OVERRIDE
# ============================================================

@router.delete(
    "/cases/{case_id}/documents/{document_id}/pages/{page_number}/ocr",
    status_code=status.HTTP_200_OK
)
async def clear_page_ocr_override(
    request: Request,
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin", "Approver", "Reviewer")),
    db: Session = Depends(get_db),
):
    """
    Clear OCR override for a page (revert to OCR text).
    
    Requires Admin, Approver, or Reviewer role.
    Tenant-scoped.
    """
    # Load Case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Load Document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Load Page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
        DocumentPage.org_id == org_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Clear override
    page.ocr_text_override = None
    page.ocr_override_updated_at = None
    page.ocr_override_user_id = None
    page.ocr_override_reason = None
    
    db.commit()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.override_cleared",
        entity_type="document_page",
        entity_id=page.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "document_id": str(document_id),
            "page_number": page_number,
            "page_id": str(page.id),
        },
    )
    
    return {"message": "Override cleared successfully", "page_id": str(page.id)}


# ============================================================
# POST OCR RERUN
# ============================================================

@router.post(
    "/cases/{case_id}/documents/{document_id}/pages/{page_number}/ocr/rerun",
    response_model=OcrRerunResponse
)
async def rerun_page_ocr(
    request: Request,
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    body: OcrRerunRequest,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin", "Approver", "Reviewer")),
    db: Session = Depends(get_db),
):
    """
    Re-run OCR for a single page with optional forced settings.
    
    Requires Admin, Approver, or Reviewer role.
    Tenant-scoped.
    Enqueues async Celery task; does not wait for completion.
    """
    # Load Case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Load Document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Load Page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number,
        DocumentPage.org_id == org_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Validate options
    if body.force_profile and body.force_profile not in ["basic", "enhanced"]:
        raise HTTPException(status_code=400, detail="force_profile must be 'basic' or 'enhanced'")
    
    if body.engine_mode and body.engine_mode not in ["tesseract", "ensemble"]:
        raise HTTPException(status_code=400, detail="engine_mode must be 'tesseract' or 'ensemble'")
    
    # Enqueue Celery task
    from app.workers.tasks_ocr_rerun import rerun_page_ocr_task
    
    request_id = uuid.uuid4()
    options = {
        "force_profile": body.force_profile,
        "force_detect": body.force_detect,
        "force_lang": body.force_lang,
        "force_layout": body.force_layout,
        "force_pdf_text_layer": body.force_pdf_text_layer,
        "engine_mode": body.engine_mode,
    }
    
    # Remove None values
    options = {k: v for k, v in options.items() if v is not None}
    
    task = rerun_page_ocr_task.delay(
        str(org_id),
        str(case_id),
        str(document_id),
        page_number,
        str(request_id),
        options
    )
    
    return OcrRerunResponse(
        queued=True,
        page_id=str(page.id),
        page_number=page_number,
        task="ocr.rerun_page",
    )

