"""Dossier Autofill API endpoints."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.case import Case
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.dossier_autofill import autofill_dossier

router = APIRouter(tags=["dossier"])


class AutofillRequest(BaseModel):
    document_ids: Optional[List[str]] = None  # Optional filter by document IDs


class ExtractedFieldResponse(BaseModel):
    field_path: str
    value: str
    confidence: float
    evidence: dict


class AutofillResponse(BaseModel):
    case_id: str
    overwrite: bool
    extracted: List[ExtractedFieldResponse]
    updated_fields: List[str]
    skipped_fields: List[str]
    errors: List[str]


@router.post("/cases/{case_id}/dossier/autofill", response_model=AutofillResponse)
async def run_autofill(
    request: Request,
    case_id: uuid.UUID,
    overwrite: bool = Query(False, description="Overwrite existing field values"),
    body: Optional[AutofillRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Autofill dossier fields from OCR text across all documents in the case.
    
    Requires Admin or Reviewer role.
    """
    # Check RBAC
    if current_user.role not in ["Admin", "Reviewer"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Reviewer roles can run autofill"
        )
    
    # Validate case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Convert document_ids to UUIDs if provided
    document_ids = None
    if body and body.document_ids:
        try:
            document_ids = [uuid.UUID(doc_id) for doc_id in body.document_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    # Run autofill
    try:
        result = autofill_dossier(
            db=db,
            org_id=current_user.org_id,
            case_id=case_id,
            user_id=current_user.user_id,
            document_ids=document_ids,
            overwrite=overwrite,
        )
    except Exception as e:
        result = {
            "extracted": [],
            "updated_fields": [],
            "skipped_fields": [],
            "errors": [f"Autofill failed: {str(e)}"],
        }
    
    # Audit log
    request_id = uuid.uuid4()
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="dossier.autofill_run",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "request_id": str(request_id),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "overwrite": overwrite,
            "extracted_count": len(result["extracted"]),
            "updated_count": len(result["updated_fields"]),
            "skipped_count": len(result["skipped_fields"]),
            "document_ids": [str(did) for did in (document_ids or [])],
        },
    )
    
    # Log individual field updates
    for field_path in result["updated_fields"]:
        write_audit_event(
            db=db,
            org_id=current_user.org_id,
            actor_user_id=current_user.user_id,
            action="dossier.field_autofilled",
            entity_type="case_dossier_field",
            entity_id=None,  # Field ID not available here
            event_metadata={
                "case_id": str(case_id),
                "field_path": field_path,
                "overwrite": overwrite,
            },
        )
    
    return AutofillResponse(
        case_id=str(case_id),
        overwrite=overwrite,
        extracted=[
            ExtractedFieldResponse(
                field_path=ef["field_path"],
                value=ef["value"],
                confidence=ef["confidence"],
                evidence=ef["evidence"],
            )
            for ef in result["extracted"]
        ],
        updated_fields=result["updated_fields"],
        skipped_fields=result["skipped_fields"],
        errors=result["errors"],
    )

