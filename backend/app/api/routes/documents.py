import uuid
from datetime import datetime
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
from app.api.deps import get_current_user, CurrentUser, require_tenant_scope
from app.services.audit import write_audit_event
from app.services.storage import put_object_bytes, get_presigned_get_url
from app.services.pdf_splitter import split_pdf, PDFSplitError
from app.services.doc_convert import convert_docx_bytes_to_pdf, DocConvertError
from app.core.middleware import sanitize_filename
from app.services.rule_engine import infer_doc_type_from_filename

router = APIRouter(tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
}
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_DOCX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
DOWNLOAD_URL_EXPIRES_SECONDS = 3600  # 1 hour


@router.post("/cases/{case_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF document, DOCX file, or image to a case (tenant-scoped)."""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Determine content type (check extension if content-type is missing/incorrect)
    content_type = file.content_type or "application/octet-stream"
    filename_lower = (file.filename or "").lower()
    
    # If content type is not recognized, try to infer from extension
    if content_type not in ALLOWED_CONTENT_TYPES:
        if filename_lower.endswith(".docx"):
            content_type = DOCX_CONTENT_TYPE
        elif filename_lower.endswith(".pdf"):
            content_type = "application/pdf"
        elif filename_lower.endswith((".png", ".jpg", ".jpeg")):
            content_type = "image/png" if filename_lower.endswith(".png") else "image/jpeg"
    
    # Validate content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF, DOCX, and image files (PNG, JPG) are allowed. Received: {content_type}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # P13: Validate DOCX size limit
    is_docx = content_type == DOCX_CONTENT_TYPE
    if is_docx and file_size > MAX_DOCX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"DOCX file too large. Maximum size is {MAX_DOCX_SIZE_BYTES // (1024 * 1024)} MB. Received: {file_size // (1024 * 1024)} MB"
        )
    
    # P13: Convert DOCX to PDF if needed
    original_mime_type = content_type
    conversion_metadata = None
    if is_docx:
        try:
            pdf_bytes, pdf_filename, conversion_metadata = convert_docx_bytes_to_pdf(
                file_content,
                file.filename or "document.docx",
                timeout_seconds=60
            )
            # Replace file_content with converted PDF
            file_content = pdf_bytes
            file_size = len(file_content)
            content_type = "application/pdf"  # Now it's a PDF
            
            # Audit: conversion success
            write_audit_event(
                db=db,
                org_id=current_user.org_id,
                actor_user_id=current_user.user_id,
                action="document.convert_docx.success",
                entity_type="document",
                entity_id=None,  # Document not created yet
                event_metadata={
                    "original_filename": file.filename,
                    "processing_seconds": conversion_metadata.get("processing_seconds"),
                    "original_size_bytes": conversion_metadata.get("original_size_bytes"),
                    "converted_size_bytes": conversion_metadata.get("converted_size_bytes"),
                },
            )
        except DocConvertError as e:
            # Audit: conversion failure
            write_audit_event(
                db=db,
                org_id=current_user.org_id,
                actor_user_id=current_user.user_id,
                action="document.convert_docx.failed",
                entity_type="document",
                entity_id=None,
                event_metadata={
                    "original_filename": file.filename,
                    "reason": str(e),
                },
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to convert DOCX to PDF: {str(e)}"
            )
        except Exception as e:
            # Audit: unexpected conversion error
            write_audit_event(
                db=db,
                org_id=current_user.org_id,
                actor_user_id=current_user.user_id,
                action="document.convert_docx.failed",
                entity_type="document",
                entity_id=None,
                event_metadata={
                    "original_filename": file.filename,
                    "reason": "Unexpected error during conversion",
                },
            )
            raise HTTPException(
                status_code=500,
                detail="An error occurred while converting the document. Please try again."
            )
    
    # Generate document ID and storage key
    document_id = uuid.uuid4()
    
    # Determine file extension based on content type (after conversion, DOCX becomes PDF)
    is_image = content_type in IMAGE_CONTENT_TYPES
    if is_image:
        ext = "png" if content_type == "image/png" else "jpg"
        original_key = f"org/{current_user.org_id}/cases/{case_id}/docs/{document_id}/original.{ext}"
    else:
        original_key = f"org/{current_user.org_id}/cases/{case_id}/docs/{document_id}/original.pdf"
    
    # Sanitize filename for safety
    default_filename = f"image.{ext}" if is_image else "document.pdf"
    safe_filename = sanitize_filename(file.filename or default_filename)
    
    # Infer document type from filename
    inferred_doc_type = infer_doc_type_from_filename(safe_filename)
    
    # Build metadata JSON (for DOCX conversion info)
    meta_json = None
    if is_docx and conversion_metadata:
        meta_json = {
            "source_format": "docx",
            "original_mime_type": original_mime_type,
            "conversion": {
                "converter": conversion_metadata.get("converter"),
                "processing_seconds": conversion_metadata.get("processing_seconds"),
                "original_size_bytes": conversion_metadata.get("original_size_bytes"),
                "converted_size_bytes": conversion_metadata.get("converted_size_bytes"),
            }
        }
    
    # Create document record (initial status)
    document = Document(
        id=document_id,
        org_id=current_user.org_id,
        case_id=case_id,
        uploader_user_id=current_user.user_id,
        original_filename=safe_filename,
        content_type=content_type,  # This is now "application/pdf" for converted DOCX
        size_bytes=file_size,
        minio_key_original=original_key,
        status="Uploaded",
        doc_type=inferred_doc_type,
        doc_type_source="auto" if inferred_doc_type else None,
        doc_type_updated_at=datetime.utcnow() if inferred_doc_type else None,
        meta_json=meta_json,
    )
    db.add(document)
    db.commit()
    
    try:
        # Upload original to MinIO (PDF after conversion, or original for PDF/images)
        put_object_bytes(original_key, file_content, content_type)
        
        if is_image:
            # For images: create single page record, no splitting
            document.page_count = 1
            document.status = "Uploaded"  # Images don't get "Split" status
            
            # Create a single page record for the image
            page_record = DocumentPage(
                org_id=current_user.org_id,
                document_id=document_id,
                page_number=1,
                minio_key_page_pdf=original_key,  # Points to original image
            )
            db.add(page_record)
            db.commit()
            db.refresh(document)
        else:
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
    
    # Audit log (include classification if inferred, and original mime type)
    request_id = uuid.uuid4()
    audit_metadata = {
        "request_id": str(request_id),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "case_id": str(case_id),
        "document_id": str(document.id),
        "filename": document.original_filename,
        "size_bytes": file_size,
        "page_count": document.page_count,
        "status": document.status,
        "is_image": is_image,
        "original_mime_type": original_mime_type,  # P13: Track original format
    }
    if inferred_doc_type:
        audit_metadata["doc_type"] = inferred_doc_type
        audit_metadata["classification_source"] = "auto"
    if is_docx:
        audit_metadata["converted_from"] = "docx"
        if conversion_metadata:
            audit_metadata["conversion_seconds"] = conversion_metadata.get("processing_seconds")
    
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.uploaded",
        entity_type="document",
        entity_id=document.id,
        event_metadata=audit_metadata,
    )
    
    return document


@router.get("/cases/{case_id}/documents", response_model=list[DocumentListItem])
async def list_documents(
    request: Request,
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for a case (tenant-scoped: 404 if case not in org)."""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
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
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document details (tenant-scoped: 404 if not in org)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == org_id,
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
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download the original document (tenant-scoped)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == org_id,
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
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed URL to download a specific page PDF (tenant-scoped)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == org_id,
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

