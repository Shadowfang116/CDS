import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document, DocumentPage
from app.schemas.document import (
    DocumentResponse,
    DocumentListItem,
    DocumentDetailResponse,
    DocumentPageResponse,
    PresignedUrlResponse,
)
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.storage import put_object_bytes, get_presigned_get_url
from app.services.pdf_splitter import split_pdf, PDFSplitError

router = APIRouter(tags=["documents"])

ALLOWED_CONTENT_TYPES = {"application/pdf"}
DOWNLOAD_URL_EXPIRES_SECONDS = 3600  # 1 hour


@router.post("/cases/{case_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF document to a case."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are allowed. Received: {content_type}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Generate document ID and storage key
    document_id = uuid.uuid4()
    original_key = f"org/{current_user.org_id}/cases/{case_id}/docs/{document_id}/original.pdf"
    
    # Create document record (initial status)
    document = Document(
        id=document_id,
        org_id=current_user.org_id,
        case_id=case_id,
        uploader_user_id=current_user.user_id,
        original_filename=file.filename or "document.pdf",
        content_type=content_type,
        size_bytes=file_size,
        minio_key_original=original_key,
        status="Uploaded",
    )
    db.add(document)
    db.commit()
    
    try:
        # Upload original to MinIO
        put_object_bytes(original_key, file_content, content_type)
        
        # Split PDF into pages
        page_count, pages = split_pdf(file_content)
        
        # Upload each page and create page records
        for page_number, page_bytes in pages:
            page_key = f"org/{current_user.org_id}/cases/{case_id}/docs/{document_id}/pages/{page_number}.pdf"
            put_object_bytes(page_key, page_bytes, "application/pdf")
            
            page_record = DocumentPage(
                org_id=current_user.org_id,
                document_id=document_id,
                page_number=page_number,
                minio_key_page_pdf=page_key,
            )
            db.add(page_record)
        
        # Update document status
        document.page_count = page_count
        document.status = "Split"
        db.commit()
        db.refresh(document)
        
    except PDFSplitError as e:
        document.status = "Failed"
        document.error_message = str(e)
        db.commit()
        db.refresh(document)
    except Exception as e:
        document.status = "Failed"
        document.error_message = f"Upload failed: {str(e)}"
        db.commit()
        db.refresh(document)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.upload",
        entity_type="document",
        entity_id=document.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "document_id": str(document.id),
            "filename": document.original_filename,
            "size_bytes": file_size,
            "page_count": document.page_count,
            "status": document.status,
        },
    )
    
    return document


@router.get("/cases/{case_id}/documents", response_model=list[DocumentListItem])
async def list_documents(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for a case."""
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).order_by(Document.created_at.desc()).all()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.list",
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "count": len(documents),
        },
    )
    
    return documents


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document details including pages."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).order_by(DocumentPage.page_number).all()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.view",
        entity_type="document",
        entity_id=document.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(document.case_id),
        },
    )
    
    # Build response with pages
    page_responses = [
        DocumentPageResponse(
            id=p.id,
            page_number=p.page_number,
            has_thumbnail=p.minio_key_thumbnail is not None,
            ocr_status=p.ocr_status,
            ocr_confidence=float(p.ocr_confidence) if p.ocr_confidence else None,
        )
        for p in pages
    ]
    
    return DocumentDetailResponse(
        id=document.id,
        org_id=document.org_id,
        case_id=document.case_id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        pages=page_responses,
    )


@router.get("/documents/{document_id}/download", response_model=PresignedUrlResponse)
async def download_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download the original document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    url = get_presigned_get_url(document.minio_key_original, DOWNLOAD_URL_EXPIRES_SECONDS)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.download",
        entity_type="document",
        entity_id=document.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(document.case_id),
        },
    )
    
    return PresignedUrlResponse(url=url, expires_in_seconds=DOWNLOAD_URL_EXPIRES_SECONDS)


@router.get("/documents/{document_id}/pages/{page_number}/download", response_model=PresignedUrlResponse)
async def download_page(
    request: Request,
    document_id: uuid.UUID,
    page_number: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download a specific page PDF."""
    # Validate document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Validate page
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
        DocumentPage.page_number == page_number,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    url = get_presigned_get_url(page.minio_key_page_pdf, DOWNLOAD_URL_EXPIRES_SECONDS)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.page_download",
        entity_type="document_page",
        entity_id=page.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "page_number": page_number,
            "case_id": str(document.case_id),
        },
    )
    
    return PresignedUrlResponse(url=url, expires_in_seconds=DOWNLOAD_URL_EXPIRES_SECONDS)

