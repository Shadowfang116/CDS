"""D6: Admin endpoints for deletion, retention, and cleanup."""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.case import Case
from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun
from app.models.export import Export
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.storage import delete_object, delete_objects_by_prefix

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: CurrentUser):
    """Check that user is Admin."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )


# ============================================================
# SCHEMAS
# ============================================================

class DeleteResponse(BaseModel):
    message: str
    deleted_db_rows: int
    deleted_minio_objects: int


class RetentionCleanupResponse(BaseModel):
    message: str
    cases_deleted: int
    cutoff_date: str


# ============================================================
# DELETE CASE
# ============================================================

@router.delete("/cases/{case_id}", response_model=DeleteResponse)
async def delete_case(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a case and all related data (Admin only).
    Removes: exports, exceptions, cps, evidence refs, dossier fields, documents, pages.
    Also removes all MinIO objects under the case prefix.
    """
    require_admin(current_user)
    
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    deleted_rows = 0
    
    # Delete exports
    exports = db.query(Export).filter(
        Export.case_id == case_id,
        Export.org_id == current_user.org_id,
    ).all()
    for exp in exports:
        db.delete(exp)
    deleted_rows += len(exports)
    
    # Delete exception evidence refs (must delete before exceptions)
    exc_ids = db.query(Exception_.id).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == current_user.org_id,
    ).all()
    exc_ids = [e[0] for e in exc_ids]
    
    if exc_ids:
        deleted = db.query(ExceptionEvidenceRef).filter(
            ExceptionEvidenceRef.exception_id.in_(exc_ids),
            ExceptionEvidenceRef.org_id == current_user.org_id,
        ).delete(synchronize_session=False)
        deleted_rows += deleted
    
    # Delete exceptions
    deleted = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete CPs
    deleted = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete rule runs
    deleted = db.query(RuleRun).filter(
        RuleRun.case_id == case_id,
        RuleRun.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete dossier fields
    deleted = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete document pages
    doc_ids = db.query(Document.id).filter(
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).all()
    doc_ids = [d[0] for d in doc_ids]
    
    if doc_ids:
        deleted = db.query(DocumentPage).filter(
            DocumentPage.document_id.in_(doc_ids),
            DocumentPage.org_id == current_user.org_id,
        ).delete(synchronize_session=False)
        deleted_rows += deleted
    
    # Delete documents
    deleted = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    # Delete case
    db.delete(case)
    deleted_rows += 1
    
    db.commit()
    
    # Delete MinIO objects
    minio_prefix = f"org/{current_user.org_id}/cases/{case_id}/"
    deleted_minio = delete_objects_by_prefix(minio_prefix)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="case.delete",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "case_title": case.title,
            "deleted_db_rows": deleted_rows,
            "deleted_minio_objects": deleted_minio,
        },
    )
    
    return DeleteResponse(
        message=f"Case '{case.title}' deleted successfully",
        deleted_db_rows=deleted_rows,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# DELETE EXPORT
# ============================================================

@router.delete("/exports/{export_id}", response_model=DeleteResponse)
async def delete_export(
    request: Request,
    export_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an export and its MinIO object (Admin only)."""
    require_admin(current_user)
    
    export = db.query(Export).filter(
        Export.id == export_id,
        Export.org_id == current_user.org_id,
    ).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    minio_key = export.minio_key
    case_id = export.case_id
    filename = export.filename
    
    db.delete(export)
    db.commit()
    
    # Delete MinIO object
    try:
        delete_object(minio_key)
        deleted_minio = 1
    except Exception as e:
        deleted_minio = 0
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.delete",
        entity_type="export",
        entity_id=export_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "export_id": str(export_id),
            "case_id": str(case_id),
            "filename": filename,
        },
    )
    
    return DeleteResponse(
        message=f"Export '{filename}' deleted successfully",
        deleted_db_rows=1,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document, its pages, and MinIO objects (Admin only)."""
    require_admin(current_user)
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    deleted_rows = 0
    
    # Delete pages
    deleted = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.org_id == current_user.org_id,
    ).delete(synchronize_session=False)
    deleted_rows += deleted
    
    case_id = document.case_id
    filename = document.original_filename
    
    # Delete document
    db.delete(document)
    deleted_rows += 1
    
    db.commit()
    
    # Delete MinIO objects for this document
    minio_prefix = f"org/{current_user.org_id}/cases/{case_id}/docs/{document_id}/"
    deleted_minio = delete_objects_by_prefix(minio_prefix)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="document.delete",
        entity_type="document",
        entity_id=document_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "document_id": str(document_id),
            "case_id": str(case_id),
            "filename": filename,
            "deleted_db_rows": deleted_rows,
            "deleted_minio_objects": deleted_minio,
        },
    )
    
    return DeleteResponse(
        message=f"Document '{filename}' deleted successfully",
        deleted_db_rows=deleted_rows,
        deleted_minio_objects=deleted_minio,
    )


# ============================================================
# RETENTION CLEANUP
# ============================================================

@router.post("/run-retention-cleanup", response_model=RetentionCleanupResponse)
async def run_retention_cleanup(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete cases older than RETENTION_DAYS (Admin only).
    This is a manual cleanup endpoint.
    """
    require_admin(current_user)
    
    retention_days = settings.RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    # Find cases older than cutoff
    old_cases = db.query(Case).filter(
        Case.org_id == current_user.org_id,
        Case.created_at < cutoff_date,
    ).all()
    
    cases_deleted = 0
    total_db_rows = 0
    total_minio_objects = 0
    
    for case in old_cases:
        # Delete all related data (same logic as delete_case)
        case_id = case.id
        
        # Delete exports
        exports = db.query(Export).filter(Export.case_id == case_id).all()
        for exp in exports:
            db.delete(exp)
        total_db_rows += len(exports)
        
        # Delete exception evidence refs
        exc_ids = [e[0] for e in db.query(Exception_.id).filter(Exception_.case_id == case_id).all()]
        if exc_ids:
            total_db_rows += db.query(ExceptionEvidenceRef).filter(
                ExceptionEvidenceRef.exception_id.in_(exc_ids)
            ).delete(synchronize_session=False)
        
        # Delete exceptions
        total_db_rows += db.query(Exception_).filter(Exception_.case_id == case_id).delete(synchronize_session=False)
        
        # Delete CPs
        total_db_rows += db.query(ConditionPrecedent).filter(ConditionPrecedent.case_id == case_id).delete(synchronize_session=False)
        
        # Delete rule runs
        total_db_rows += db.query(RuleRun).filter(RuleRun.case_id == case_id).delete(synchronize_session=False)
        
        # Delete dossier fields
        total_db_rows += db.query(CaseDossierField).filter(CaseDossierField.case_id == case_id).delete(synchronize_session=False)
        
        # Delete document pages
        doc_ids = [d[0] for d in db.query(Document.id).filter(Document.case_id == case_id).all()]
        if doc_ids:
            total_db_rows += db.query(DocumentPage).filter(DocumentPage.document_id.in_(doc_ids)).delete(synchronize_session=False)
        
        # Delete documents
        total_db_rows += db.query(Document).filter(Document.case_id == case_id).delete(synchronize_session=False)
        
        # Delete case
        db.delete(case)
        total_db_rows += 1
        
        # Delete MinIO objects
        minio_prefix = f"org/{current_user.org_id}/cases/{case_id}/"
        total_minio_objects += delete_objects_by_prefix(minio_prefix)
        
        cases_deleted += 1
    
    db.commit()
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="retention.run",
        entity_type="system",
        entity_id=None,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "cases_deleted": cases_deleted,
            "total_db_rows": total_db_rows,
            "total_minio_objects": total_minio_objects,
        },
    )
    
    return RetentionCleanupResponse(
        message=f"Retention cleanup completed. Deleted {cases_deleted} cases older than {retention_days} days.",
        cases_deleted=cases_deleted,
        cutoff_date=cutoff_date.isoformat(),
    )

