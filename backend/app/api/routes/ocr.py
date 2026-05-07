"""OCR API endpoints."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.document import Document, DocumentPage
from app.api.deps import CurrentUser, require_reviewer, require_viewer
from app.services.audit import write_audit_event
from app.workers.tasks_ocr import process_document_ocr
from app.core.config import settings

router = APIRouter(tags=["ocr"])
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/tif"}


class OCREnqueueResponse(BaseModel):
    status: str
    document_id: str
    task_id: Optional[str] = None


class OCRPageStatus(BaseModel):
    page_number: int
    status: str
    error: Optional[str] = None
    has_text: bool = False
    
    class Config:
        from_attributes = True


class OCRStatusResponse(BaseModel):
    document_id: str
    total_pages: int
    queued_count: int
    processing_count: int
    done_count: int
    failed_count: int
    status_counts: dict
    last_error: Optional[str] = None
    pages: list[OCRPageStatus]
    # Quality metrics
    average_ocr_chars_per_page: Optional[float] = None
    failed_pages: list[dict] = []  # [{page_number: int, error: str}]
    processing_seconds: Optional[float] = None
    # Quality gate (P10)
    quality_level: Optional[str] = None  # "Good" | "Low" | "Critical"
    quality_reasons: list[str] = []  # Reasons for quality level
    # OCR metadata (P8)
    ocr_lang_used: Optional[str] = None
    dpi_used: Optional[int] = None
    preprocess_enabled: Optional[bool] = None


class DocTypeUpdateRequest(BaseModel):
    doc_type: str


class DocTypeResponse(BaseModel):
    id: str
    doc_type: Optional[str]
    doc_type_source: Optional[str]
    doc_type_updated_at: Optional[datetime]


@router.post("/documents/{document_id}/ocr", response_model=OCREnqueueResponse)
async def enqueue_document_ocr(
    request: Request,
    document_id: uuid.UUID,
    force: bool = False,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """Enqueue OCR processing for a document's pages. Use force=true to re-process Done pages."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    expected_status = "Uploaded" if document.content_type in IMAGE_CONTENT_TYPES else "Split"
    if document.status != expected_status:
        raise HTTPException(
            status_code=400, 
            detail=f"Document must be in '{expected_status}' status to run OCR. Current status: {document.status}"
        )

    page_count = (
        db.query(func.count(DocumentPage.id))
        .filter(
            DocumentPage.document_id == document_id,
            DocumentPage.org_id == current_user.org_id,
        )
        .scalar()
        or 0
    )
    if page_count == 0:
        raise HTTPException(status_code=400, detail="Document has no pages available for OCR")

    document.status = "Queued"
    db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).update(
        {
            DocumentPage.ocr_status: "Queued",
            DocumentPage.ocr_error: None,
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(document)

    task = process_document_ocr.apply_async(
        args=[str(document_id), str(current_user.org_id), str(current_user.user_id)],
        kwargs={"force": force},
    )

    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.ocr_enqueued",
        entity_type="document",
        entity_id=document_id,
        case_id=document.case_id,
        ip_address=request.client.host if request.client else None,
        event_metadata={
            "document_id": str(document_id),
            "case_id": str(document.case_id),
            "filename": document.original_filename,
            "task_id": task.id,
            "force": force,
            "page_count": page_count,
            "status": document.status,
        },
    )
    
    return OCREnqueueResponse(
        status="queued",
        document_id=str(document_id),
        task_id=task.id,
    )


@router.get("/documents/{document_id}/ocr-status", response_model=OCRStatusResponse)
async def get_ocr_status(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get OCR processing status for a document."""
    # Validate document exists and belongs to org
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get pages with OCR status
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).order_by(DocumentPage.page_number).all()
    
    # Calculate status counts
    status_counts = {}
    queued_count = 0
    processing_count = 0
    done_count = 0
    failed_count = 0
    last_error = None
    
    for page in pages:
        status = page.ocr_status
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status == "Queued":
            queued_count += 1
        elif status == "Processing":
            processing_count += 1
        elif status == "Done":
            done_count += 1
        elif status == "Failed":
            failed_count += 1
            if page.ocr_error and (not last_error or page.ocr_finished_at):
                # Get most recent error
                last_error = page.ocr_error
    
    # Build page status list and calculate quality metrics
    page_statuses = []
    failed_pages_list = []
    total_chars = 0
    done_pages_count = 0
    processing_times = []
    
    for p in pages:
        page_statuses.append(OCRPageStatus(
            page_number=p.page_number,
            status=p.ocr_status,
            error=p.ocr_error,
            has_text=bool(p.ocr_text),
        ))
        
        # Collect failed pages
        if p.ocr_status == "Failed":
            failed_pages_list.append({
                "page_number": p.page_number,
                "error": p.ocr_error or "Unknown error"
            })
        
        # Calculate average chars per page (only for Done pages)
        if p.ocr_status == "Done" and p.ocr_text:
            char_count = len(p.ocr_text)
            total_chars += char_count
            done_pages_count += 1
        
        # Calculate processing time (if timestamps available)
        if p.ocr_started_at and p.ocr_finished_at:
            from datetime import datetime
            if isinstance(p.ocr_started_at, datetime) and isinstance(p.ocr_finished_at, datetime):
                delta = (p.ocr_finished_at - p.ocr_started_at).total_seconds()
                processing_times.append(delta)
    
    # Calculate metrics
    average_chars = total_chars / done_pages_count if done_pages_count > 0 else None
    processing_seconds = max(processing_times) if processing_times else None
    
    # P10: Quality gate
    quality_level = "Good"
    quality_reasons = []
    
    if done_pages_count > 0:
        # Check average chars per page
        if average_chars and average_chars < 80:
            quality_level = "Low"
            quality_reasons.append(f"Low average characters per page ({average_chars:.0f} < 80)")
        
        # Check failed pages
        failed_pct = (failed_count / len(pages)) * 100 if len(pages) > 0 else 0
        if failed_count > 0:
            if failed_pct > 20:
                quality_level = "Critical"
                quality_reasons.append(f"High failure rate ({failed_pct:.0f}% pages failed)")
            else:
                if quality_level == "Good":
                    quality_level = "Low"
                quality_reasons.append(f"{failed_count} page(s) failed OCR")
        
        # Check processing time (warning only, doesn't change level)
        if processing_seconds and processing_seconds > 120:
            quality_reasons.append(f"Slow processing ({processing_seconds:.0f}s per page)")
    elif len(pages) == 0:
        quality_level = "Low"
        quality_reasons.append("No pages processed yet")
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="ocr.status_check",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
        },
    )
    
    # Get OCR metadata from config (same for all pages)
    lang_used = settings.OCR_LANG
    # Check if Urdu was requested but not available (best-effort)
    try:
        import pytesseract
        available_langs = pytesseract.get_languages()
        if "urd" in lang_used.split("+") and "urd" not in available_langs:
            lang_used = "eng"
    except Exception:
        pass
    
    return OCRStatusResponse(
        document_id=str(document_id),
        total_pages=len(pages),
        queued_count=queued_count,
        processing_count=processing_count,
        done_count=done_count,
        failed_count=failed_count,
        status_counts=status_counts,
        last_error=last_error,
        pages=page_statuses,
        average_ocr_chars_per_page=average_chars,
        failed_pages=failed_pages_list,
        processing_seconds=processing_seconds,
        quality_level=quality_level,
        quality_reasons=quality_reasons,
        ocr_lang_used=lang_used,
        dpi_used=settings.OCR_DPI,
        preprocess_enabled=settings.OCR_ENABLE_PREPROCESS,
    )


@router.patch("/documents/{document_id}/doc-type", response_model=DocTypeResponse)
async def update_doc_type(
    request: Request,
    document_id: uuid.UUID,
    body: DocTypeUpdateRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """Manually set/override document type."""
    # Validate document exists and belongs to org
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update doc_type fields
    document.doc_type = body.doc_type
    document.doc_type_source = "manual"
    document.doc_type_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.doc_type_update",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(document.case_id),
            "doc_type": body.doc_type,
        },
    )
    
    return DocTypeResponse(
        id=str(document.id),
        doc_type=document.doc_type,
        doc_type_source=document.doc_type_source,
        doc_type_updated_at=document.doc_type_updated_at,
    )


@router.post("/documents/{document_id}/retry-ocr", response_model=OCREnqueueResponse)
async def retry_document_ocr(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status != "Failed":
        raise HTTPException(status_code=422, detail="Retry is only available for failed documents.")

    db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).update(
        {
            DocumentPage.ocr_status: "Queued",
            DocumentPage.ocr_error: None,
            DocumentPage.ocr_started_at: None,
            DocumentPage.ocr_finished_at: None,
        },
        synchronize_session=False,
    )
    document.status = "Queued"
    document.error_message = None
    db.commit()

    task = process_document_ocr.apply_async(
        args=[str(document_id), str(current_user.org_id), str(current_user.user_id)],
        kwargs={"force": True},
    )
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.ocr_retry_enqueued",
        entity_type="document",
        entity_id=document_id,
        case_id=document.case_id,
        event_metadata={"task_id": task.id},
        request_id=getattr(request.state, "request_id", None),
    )
    return OCREnqueueResponse(status="queued", document_id=str(document_id), task_id=task.id)

