"""D5: Exports API endpoints for drafts and bank pack."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case import Case
from app.models.org import Org
from app.models.user import User
from app.models.document import Document, CaseDossierField
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef
from app.models.export import Export
from app.models.verification import Verification, VerificationEvidenceRef
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.storage import put_object_bytes, get_presigned_get_url
from app.services.export_drafts import (
    generate_discrepancy_letter,
    generate_undertaking_indemnity,
    generate_internal_opinion_skeleton,
)
from app.services.export_bank_pack import generate_bank_pack_pdf

router = APIRouter(tags=["exports"])

DOWNLOAD_EXPIRES_SECONDS = 3600  # 1 hour


# ============================================================
# SCHEMAS
# ============================================================

class ExportResponse(BaseModel):
    export_id: str
    filename: str
    export_type: str
    url: str
    expires_in_seconds: int
    created_at: datetime


class ExportListItem(BaseModel):
    id: str
    export_type: str
    filename: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExportsListResponse(BaseModel):
    case_id: str
    exports: List[ExportListItem]
    total: int


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int
    filename: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _load_case_data(db: Session, case_id: uuid.UUID, org_id: uuid.UUID):
    """Load all case data for export generation."""
    # Get case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get org
    org = db.query(Org).filter(Org.id == org_id).first()
    
    # Get dossier fields
    dossier_rows = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
    ).all()
    
    dossier = {}
    dossier_fields_list = []  # Full field objects with source info
    for row in dossier_rows:
        if row.field_value:
            if row.field_key not in dossier:
                dossier[row.field_key] = []
            dossier[row.field_key].append(row.field_value)
        
        # Build dossier fields list with source info
        dossier_fields_list.append({
            "field_key": row.field_key,
            "field_value": row.field_value,
            "source_document_id": str(row.source_document_id) if row.source_document_id else None,
            "source_page_number": row.source_page_number,
        })
    
    # Get exceptions
    exceptions = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
    ).order_by(Exception_.severity.desc(), Exception_.created_at).all()
    
    exceptions_list = [
        {
            "id": str(e.id),
            "rule_id": e.rule_id,
            "module": e.module,
            "severity": e.severity,
            "title": e.title,
            "description": e.description,
            "cp_text": e.cp_text,
            "resolution_conditions": e.resolution_conditions,
            "status": e.status,
            "waiver_reason": e.waiver_reason,
        }
        for e in exceptions
    ]
    
    # Get CPs
    cps = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
    ).order_by(ConditionPrecedent.severity.desc(), ConditionPrecedent.created_at).all()
    
    cps_list = [
        {
            "id": str(c.id),
            "rule_id": c.rule_id,
            "severity": c.severity,
            "text": c.text,
            "evidence_required": c.evidence_required,
            "status": c.status,
        }
        for c in cps
    ]
    
    # Get documents
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).all()
    
    documents_list = [
        {
            "id": str(d.id),
            "original_filename": d.original_filename,
            "doc_type": d.doc_type,
            "page_count": d.page_count,
        }
        for d in documents
    ]
    
    # Get evidence refs
    exception_ids = [e.id for e in exceptions]
    evidence_refs = db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.exception_id.in_(exception_ids),
        ExceptionEvidenceRef.org_id == org_id,
    ).all()
    
    evidence_refs_map = {}
    for ref in evidence_refs:
        exc_id = str(ref.exception_id)
        if exc_id not in evidence_refs_map:
            evidence_refs_map[exc_id] = []
        evidence_refs_map[exc_id].append({
            "document_id": str(ref.document_id) if ref.document_id else None,
            "page_number": ref.page_number,
            "note": ref.note,
        })
    
    # Get verifications
    verifications = db.query(Verification).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
    ).all()
    
    # Build document lookup for verification evidence
    doc_lookup = {str(d.id): d for d in documents}
    
    verifications_list = []
    for v in verifications:
        # Get verified_by user email
        verified_by_email = None
        if v.verified_by_user_id:
            user = db.query(User).filter(User.id == v.verified_by_user_id).first()
            if user:
                verified_by_email = user.email
        
        # Get verification evidence refs
        v_evidence_refs = db.query(VerificationEvidenceRef).filter(
            VerificationEvidenceRef.verification_id == v.id,
            VerificationEvidenceRef.org_id == org_id,
        ).all()
        
        v_evidence_list = []
        for ve in v_evidence_refs:
            doc_id_str = str(ve.document_id) if ve.document_id else None
            doc = doc_lookup.get(doc_id_str)
            v_evidence_list.append({
                "document_id": doc_id_str,
                "filename": doc.original_filename if doc else "Unknown",
                "page_number": ve.page_number,
                "note": ve.note,
            })
        
        verifications_list.append({
            "id": str(v.id),
            "verification_type": v.verification_type,
            "status": v.status,
            "keys_json": v.keys_json or {},
            "notes": v.notes,
            "verified_by_email": verified_by_email,
            "verified_at": v.verified_at.isoformat() if v.verified_at else None,
            "evidence_refs": v_evidence_list,
        })
    
    return {
        "case": {"id": str(case.id), "title": case.title, "status": case.status},
        "org": {"id": str(org.id), "name": org.name} if org else {"id": str(org_id), "name": "Organization"},
        "dossier": dossier,
        "exceptions": exceptions_list,
        "cps": cps_list,
        "documents": documents_list,
        "evidence_refs": evidence_refs_map,
        "verifications": verifications_list,
        "dossier_fields": dossier_fields_list,
    }


def _store_export(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    export_type: str,
    content_type: str,
    data: bytes,
    filename: str,
) -> tuple:
    """Store export in MinIO and create DB record."""
    export_id = uuid.uuid4()
    minio_key = f"org/{org_id}/cases/{case_id}/exports/{export_id}/{filename}"
    
    # Upload to MinIO
    put_object_bytes(minio_key, data, content_type)
    
    # Create export record
    export = Export(
        id=export_id,
        org_id=org_id,
        case_id=case_id,
        export_type=export_type,
        filename=filename,
        content_type=content_type,
        minio_key=minio_key,
        created_by_user_id=user_id,
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    
    # Generate presigned URL
    url = get_presigned_get_url(minio_key, DOWNLOAD_EXPIRES_SECONDS)
    
    return export, url


# ============================================================
# DRAFT ENDPOINTS
# ============================================================

@router.post("/cases/{case_id}/drafts/discrepancy-letter", response_model=ExportResponse)
async def generate_discrepancy_letter_draft(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a discrepancy letter DOCX."""
    data = _load_case_data(db, case_id, current_user.org_id)
    
    # Generate DOCX
    doc_bytes, filename = generate_discrepancy_letter(
        case=data["case"],
        org=data["org"],
        dossier=data["dossier"],
        exceptions=data["exceptions"],
        cps=data["cps"],
    )
    
    # Store export
    export, url = _store_export(
        db=db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        export_type="discrepancy_letter",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data=doc_bytes,
        filename=filename,
    )
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.generate",
        entity_type="export",
        entity_id=export.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "export_id": str(export.id),
            "export_type": "discrepancy_letter",
            "filename": filename,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",
        payload={
            "export_id": str(export.id),
            "export_type": "discrepancy_letter",
            "filename": filename,
            "case_id": str(case_id),
            "case_title": data["case"]["title"],
        },
    )
    
    return ExportResponse(
        export_id=str(export.id),
        filename=filename,
        export_type="discrepancy_letter",
        url=url,
        expires_in_seconds=DOWNLOAD_EXPIRES_SECONDS,
        created_at=export.created_at,
    )


@router.post("/cases/{case_id}/drafts/undertaking-indemnity", response_model=ExportResponse)
async def generate_undertaking_indemnity_draft(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an undertaking and indemnity DOCX."""
    data = _load_case_data(db, case_id, current_user.org_id)
    
    # Generate DOCX
    doc_bytes, filename = generate_undertaking_indemnity(
        case=data["case"],
        org=data["org"],
        dossier=data["dossier"],
        exceptions=data["exceptions"],
        cps=data["cps"],
    )
    
    # Store export
    export, url = _store_export(
        db=db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        export_type="undertaking_indemnity",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data=doc_bytes,
        filename=filename,
    )
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.generate",
        entity_type="export",
        entity_id=export.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "export_id": str(export.id),
            "export_type": "undertaking_indemnity",
            "filename": filename,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",
        payload={
            "export_id": str(export.id),
            "export_type": "undertaking_indemnity",
            "filename": filename,
            "case_id": str(case_id),
            "case_title": data["case"]["title"],
        },
    )
    
    return ExportResponse(
        export_id=str(export.id),
        filename=filename,
        export_type="undertaking_indemnity",
        url=url,
        expires_in_seconds=DOWNLOAD_EXPIRES_SECONDS,
        created_at=export.created_at,
    )


@router.post("/cases/{case_id}/drafts/internal-opinion", response_model=ExportResponse)
async def generate_internal_opinion_draft(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an internal legal opinion skeleton DOCX."""
    data = _load_case_data(db, case_id, current_user.org_id)
    
    # Generate DOCX
    doc_bytes, filename = generate_internal_opinion_skeleton(
        case=data["case"],
        org=data["org"],
        dossier=data["dossier"],
        exceptions=data["exceptions"],
        cps=data["cps"],
    )
    
    # Store export
    export, url = _store_export(
        db=db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        export_type="internal_opinion",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data=doc_bytes,
        filename=filename,
    )
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.generate",
        entity_type="export",
        entity_id=export.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "export_id": str(export.id),
            "export_type": "internal_opinion",
            "filename": filename,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",
        payload={
            "export_id": str(export.id),
            "export_type": "internal_opinion",
            "filename": filename,
            "case_id": str(case_id),
            "case_title": data["case"]["title"],
        },
    )
    
    return ExportResponse(
        export_id=str(export.id),
        filename=filename,
        export_type="internal_opinion",
        url=url,
        expires_in_seconds=DOWNLOAD_EXPIRES_SECONDS,
        created_at=export.created_at,
    )


# ============================================================
# BANK PACK ENDPOINT
# ============================================================

@router.post("/cases/{case_id}/exports/bank-pack", response_model=ExportResponse)
async def generate_bank_pack(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a Bank Pack PDF. Requires authenticated user with access to the case."""
    # Verify case belongs to user's org (enforced by _load_case_data)
    data = _load_case_data(db, case_id, current_user.org_id)
    
    # Generate PDF
    pdf_bytes, filename = generate_bank_pack_pdf(
        case=data["case"],
        org=data["org"],
        dossier=data["dossier"],
        exceptions=data["exceptions"],
        cps=data["cps"],
        documents=data["documents"],
        evidence_refs=data["evidence_refs"],
        verifications=data.get("verifications", []),
        dossier_fields=data.get("dossier_fields", []),
    )
    
    # Store export
    export, url = _store_export(
        db=db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        export_type="bank_pack_pdf",
        content_type="application/pdf",
        data=pdf_bytes,
        filename=filename,
    )
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.generate",
        entity_type="export",
        entity_id=export.id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "export_id": str(export.id),
            "export_type": "bank_pack_pdf",
            "filename": filename,
        },
    )
    
    # Emit integration event
    from app.services.event_bus import emit_event
    emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",
        payload={
            "export_id": str(export.id),
            "export_type": "bank_pack_pdf",
            "filename": filename,
            "case_id": str(case_id),
            "case_title": data["case"]["title"],
        },
    )
    
    return ExportResponse(
        export_id=str(export.id),
        filename=filename,
        export_type="bank_pack_pdf",
        url=url,
        expires_in_seconds=DOWNLOAD_EXPIRES_SECONDS,
        created_at=export.created_at,
    )


# ============================================================
# LIST AND DOWNLOAD ENDPOINTS
# ============================================================

@router.get("/cases/{case_id}/exports", response_model=ExportsListResponse)
async def list_exports(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all exports for a case."""
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get exports
    exports = db.query(Export).filter(
        Export.case_id == case_id,
        Export.org_id == current_user.org_id,
    ).order_by(Export.created_at.desc()).all()
    
    export_list = [
        ExportListItem(
            id=str(e.id),
            export_type=e.export_type,
            filename=e.filename,
            created_at=e.created_at,
        )
        for e in exports
    ]
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.list",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "count": len(exports),
        },
    )
    
    return ExportsListResponse(
        case_id=str(case_id),
        exports=export_list,
        total=len(exports),
    )


@router.get("/exports/{export_id}/download", response_model=DownloadResponse)
async def download_export(
    request: Request,
    export_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a fresh presigned URL for an export."""
    export = db.query(Export).filter(
        Export.id == export_id,
        Export.org_id == current_user.org_id,
    ).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    # Generate presigned URL
    url = get_presigned_get_url(export.minio_key, DOWNLOAD_EXPIRES_SECONDS)
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="export.download",
        entity_type="export",
        entity_id=export_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "export_id": str(export_id),
            "case_id": str(export.case_id),
            "export_type": export.export_type,
            "filename": export.filename,
        },
    )
    
    return DownloadResponse(
        url=url,
        expires_in_seconds=DOWNLOAD_EXPIRES_SECONDS,
        filename=export.filename,
    )

