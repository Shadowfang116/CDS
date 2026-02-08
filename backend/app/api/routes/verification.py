"""Verification API routes for e-Stamp and Registry/ROD assisted verification."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.case import Case
from app.models.document import Document
from app.models.verification import Verification, VerificationEvidenceRef
from app.models.rules import ConditionPrecedent
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event

router = APIRouter(prefix="/cases/{case_id}/verifications", tags=["verification"])

VERIFICATION_TYPES = {"e_stamp", "registry_rod"}

# Mapping of verification types to rule IDs for CP satisfaction
VERIFICATION_CP_RULES = {
    "e_stamp": "EST-VERIFY-01",
    "registry_rod": "REG-VERIFY-01",
}


# ============================================================
# SCHEMAS
# ============================================================

class VerificationEvidenceRefResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationResponse(BaseModel):
    id: uuid.UUID
    verification_type: str
    status: str
    keys_json: Optional[dict]
    notes: Optional[str]
    verified_by_user_id: Optional[uuid.UUID]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    evidence_refs: List[VerificationEvidenceRefResponse] = []

    class Config:
        from_attributes = True


class UpdateKeysRequest(BaseModel):
    keys_json: Optional[dict] = None
    notes: Optional[str] = None


class AttachEvidenceRequest(BaseModel):
    document_id: uuid.UUID
    page_number: int = 1
    note: Optional[str] = None


class MarkFailedRequest(BaseModel):
    notes: str


class MarkVerifiedRequest(BaseModel):
    force: Optional[bool] = False


class PortalResponse(BaseModel):
    url: str
    guidance_steps: List[str]


# ============================================================
# HELPERS
# ============================================================

def get_or_create_verifications(db: Session, org_id: uuid.UUID, case_id: uuid.UUID) -> List[Verification]:
    """Ensure both verification types exist for a case, creating if missing."""
    verifications = db.query(Verification).filter(
        Verification.org_id == org_id,
        Verification.case_id == case_id,
    ).all()
    
    existing_types = {v.verification_type for v in verifications}
    
    for vtype in VERIFICATION_TYPES:
        if vtype not in existing_types:
            new_verification = Verification(
                org_id=org_id,
                case_id=case_id,
                verification_type=vtype,
                status="Pending",
                keys_json={},
            )
            db.add(new_verification)
            verifications.append(new_verification)
    
    if len(existing_types) < len(VERIFICATION_TYPES):
        db.commit()
        for v in verifications:
            db.refresh(v)
    
    return verifications


def satisfy_related_cps(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    verification_type: str,
    user_id: uuid.UUID,
):
    """Satisfy CPs related to the verification type."""
    rule_id = VERIFICATION_CP_RULES.get(verification_type)
    if not rule_id:
        return 0
    
    # Find open CPs for this rule
    open_cps = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.rule_id == rule_id,
        ConditionPrecedent.status == "Open",
    ).all()
    
    now = datetime.utcnow()
    for cp in open_cps:
        cp.status = "Satisfied"
        cp.satisfied_by_verification_type = verification_type
        cp.satisfied_at = now
        cp.satisfied_by_user_id = user_id
    
    db.commit()
    return len(open_cps)


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("", response_model=List[VerificationResponse])
async def list_verifications(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all verification items for a case (creates if missing)."""
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    verifications = get_or_create_verifications(db, current_user.org_id, case_id)
    
    # Load evidence refs for each verification
    result = []
    for v in verifications:
        evidence_refs = db.query(VerificationEvidenceRef).filter(
            VerificationEvidenceRef.org_id == current_user.org_id,
            VerificationEvidenceRef.verification_id == v.id,
        ).all()
        
        result.append(VerificationResponse(
            id=v.id,
            verification_type=v.verification_type,
            status=v.status,
            keys_json=v.keys_json,
            notes=v.notes,
            verified_by_user_id=v.verified_by_user_id,
            verified_at=v.verified_at,
            created_at=v.created_at,
            updated_at=v.updated_at,
            evidence_refs=[
                VerificationEvidenceRefResponse(
                    id=e.id,
                    document_id=e.document_id,
                    page_number=e.page_number,
                    note=e.note,
                    created_at=e.created_at,
                )
                for e in evidence_refs
            ],
        ))
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.list",
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "count": len(result),
        },
    )
    
    return result


@router.patch("/{verification_type}", response_model=VerificationResponse)
async def update_verification_keys(
    request: Request,
    case_id: uuid.UUID,
    verification_type: str,
    body: UpdateKeysRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update verification keys and notes."""
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid verification type: {verification_type}")
    
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Ensure verifications exist
    get_or_create_verifications(db, current_user.org_id, case_id)
    
    verification = db.query(Verification).filter(
        Verification.org_id == current_user.org_id,
        Verification.case_id == case_id,
        Verification.verification_type == verification_type,
    ).first()
    
    if body.keys_json is not None:
        verification.keys_json = body.keys_json
    if body.notes is not None:
        verification.notes = body.notes
    
    db.commit()
    db.refresh(verification)
    
    # Load evidence refs
    evidence_refs = db.query(VerificationEvidenceRef).filter(
        VerificationEvidenceRef.org_id == current_user.org_id,
        VerificationEvidenceRef.verification_id == verification.id,
    ).all()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.update_keys",
        entity_type="verification",
        entity_id=verification.id,
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "verification_type": verification_type,
            "keys_json": body.keys_json,
        },
    )
    
    return VerificationResponse(
        id=verification.id,
        verification_type=verification.verification_type,
        status=verification.status,
        keys_json=verification.keys_json,
        notes=verification.notes,
        verified_by_user_id=verification.verified_by_user_id,
        verified_at=verification.verified_at,
        created_at=verification.created_at,
        updated_at=verification.updated_at,
        evidence_refs=[
            VerificationEvidenceRefResponse(
                id=e.id,
                document_id=e.document_id,
                page_number=e.page_number,
                note=e.note,
                created_at=e.created_at,
            )
            for e in evidence_refs
        ],
    )


@router.post("/{verification_type}/open-portal", response_model=PortalResponse)
async def open_verification_portal(
    request: Request,
    case_id: uuid.UUID,
    verification_type: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portal URL for verification (logs audit event)."""
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid verification type: {verification_type}")
    
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get portal URL from settings
    if verification_type == "e_stamp":
        url = settings.ESTAMP_VERIFY_URL
        guidance_steps = [
            "1. Open the e-Stamp verification portal in a new tab",
            "2. Enter the stamp certificate number from the keys section",
            "3. Complete any CAPTCHA verification",
            "4. Take a screenshot of the verification result",
            "5. Upload the screenshot as evidence",
            "6. Mark as Verified or Failed based on the result",
        ]
    else:  # registry_rod
        url = settings.REGISTRY_VERIFY_URL
        guidance_steps = [
            "1. Open the Registry/ROD portal in a new tab",
            "2. Enter the registration number and year",
            "3. Complete any CAPTCHA verification",
            "4. Take a screenshot of the verification result",
            "5. Upload the screenshot as evidence",
            "6. Mark as Verified or Failed based on the result",
        ]
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.open_portal",
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "verification_type": verification_type,
            "portal_url": url,
        },
    )
    
    return PortalResponse(url=url, guidance_steps=guidance_steps)


@router.post("/{verification_type}/attach-evidence", response_model=VerificationEvidenceRefResponse)
async def attach_evidence(
    request: Request,
    case_id: uuid.UUID,
    verification_type: str,
    body: AttachEvidenceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach an evidence document to verification."""
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid verification type: {verification_type}")
    
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate document exists and belongs to same org
    document = db.query(Document).filter(
        Document.id == body.document_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Ensure verification exists
    get_or_create_verifications(db, current_user.org_id, case_id)
    
    verification = db.query(Verification).filter(
        Verification.org_id == current_user.org_id,
        Verification.case_id == case_id,
        Verification.verification_type == verification_type,
    ).first()
    
    # Create evidence ref
    evidence_ref = VerificationEvidenceRef(
        org_id=current_user.org_id,
        verification_id=verification.id,
        document_id=body.document_id,
        page_number=body.page_number,
        note=body.note,
    )
    db.add(evidence_ref)
    db.commit()
    db.refresh(evidence_ref)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.evidence_attach",
        entity_type="verification",
        entity_id=verification.id,
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "verification_type": verification_type,
            "document_id": str(body.document_id),
            "page_number": body.page_number,
        },
    )
    
    return VerificationEvidenceRefResponse(
        id=evidence_ref.id,
        document_id=evidence_ref.document_id,
        page_number=evidence_ref.page_number,
        note=evidence_ref.note,
        created_at=evidence_ref.created_at,
    )


@router.post("/{verification_type}/mark-verified", response_model=VerificationResponse)
async def mark_verified(
    request: Request,
    case_id: uuid.UUID,
    verification_type: str,
    body: MarkVerifiedRequest = Body(default=MarkVerifiedRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark verification as verified (requires evidence, unless force=true and Admin)."""
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid verification type: {verification_type}")
    
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Ensure verification exists
    get_or_create_verifications(db, current_user.org_id, case_id)
    
    verification = db.query(Verification).filter(
        Verification.org_id == current_user.org_id,
        Verification.case_id == case_id,
        Verification.verification_type == verification_type,
    ).first()
    
    # Check evidence exists (unless force=true and Admin)
    evidence_count = db.query(VerificationEvidenceRef).filter(
        VerificationEvidenceRef.org_id == current_user.org_id,
        VerificationEvidenceRef.verification_id == verification.id,
    ).count()
    
    if evidence_count == 0:
        if body.force and current_user.role == "Admin":
            # Admin can bypass evidence requirement with force=true
            pass
        else:
            raise HTTPException(
                status_code=400,
                detail="Evidence required. Please attach evidence first, or set force=true (Admin only)."
            )
    
    # Update verification
    verification.status = "Verified"
    verification.verified_by_user_id = current_user.user_id
    verification.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(verification)
    
    # Satisfy related CPs
    cps_satisfied = satisfy_related_cps(
        db, current_user.org_id, case_id, verification_type, current_user.user_id
    )
    
    # Load evidence refs
    evidence_refs = db.query(VerificationEvidenceRef).filter(
        VerificationEvidenceRef.org_id == current_user.org_id,
        VerificationEvidenceRef.verification_id == verification.id,
    ).all()
    
    # Audit log
    audit_metadata = {
        "request_id": str(uuid.uuid4()),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "case_id": str(case_id),
        "verification_type": verification_type,
        "cps_satisfied": cps_satisfied,
    }
    if body.force and evidence_count == 0:
        audit_metadata["force_no_evidence"] = True
    
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.mark_verified",
        entity_type="verification",
        entity_id=verification.id,
        event_metadata=audit_metadata,
    )
    
    # Also log CP satisfaction if any were satisfied
    if cps_satisfied > 0:
        write_audit_event(
            db=db,
            org_id=current_user.org_id,
            actor_user_id=current_user.user_id,
            action="cp.satisfied",
            event_metadata={
                "request_id": str(uuid.uuid4()),
                "ip": request.client.host if request.client else None,
                "case_id": str(case_id),
                "verification_type": verification_type,
                "cps_satisfied": cps_satisfied,
                "rule_id": VERIFICATION_CP_RULES.get(verification_type),
            },
        )
    
    return VerificationResponse(
        id=verification.id,
        verification_type=verification.verification_type,
        status=verification.status,
        keys_json=verification.keys_json,
        notes=verification.notes,
        verified_by_user_id=verification.verified_by_user_id,
        verified_at=verification.verified_at,
        created_at=verification.created_at,
        updated_at=verification.updated_at,
        evidence_refs=[
            VerificationEvidenceRefResponse(
                id=e.id,
                document_id=e.document_id,
                page_number=e.page_number,
                note=e.note,
                created_at=e.created_at,
            )
            for e in evidence_refs
        ],
    )


@router.post("/{verification_type}/mark-failed", response_model=VerificationResponse)
async def mark_failed(
    request: Request,
    case_id: uuid.UUID,
    verification_type: str,
    body: MarkFailedRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark verification as failed."""
    if verification_type not in VERIFICATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid verification type: {verification_type}")
    
    # Validate case
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Ensure verification exists
    get_or_create_verifications(db, current_user.org_id, case_id)
    
    verification = db.query(Verification).filter(
        Verification.org_id == current_user.org_id,
        Verification.case_id == case_id,
        Verification.verification_type == verification_type,
    ).first()
    
    # Update verification
    verification.status = "Failed"
    verification.notes = body.notes
    db.commit()
    db.refresh(verification)
    
    # Load evidence refs
    evidence_refs = db.query(VerificationEvidenceRef).filter(
        VerificationEvidenceRef.org_id == current_user.org_id,
        VerificationEvidenceRef.verification_id == verification.id,
    ).all()
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="verification.mark_failed",
        entity_type="verification",
        entity_id=verification.id,
        event_metadata={
            "request_id": str(uuid.uuid4()),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "case_id": str(case_id),
            "verification_type": verification_type,
            "notes": body.notes,
        },
    )
    
    return VerificationResponse(
        id=verification.id,
        verification_type=verification.verification_type,
        status=verification.status,
        keys_json=verification.keys_json,
        notes=verification.notes,
        verified_by_user_id=verification.verified_by_user_id,
        verified_at=verification.verified_at,
        created_at=verification.created_at,
        updated_at=verification.updated_at,
        evidence_refs=[
            VerificationEvidenceRefResponse(
                id=e.id,
                document_id=e.document_id,
                page_number=e.page_number,
                note=e.note,
                created_at=e.created_at,
            )
            for e in evidence_refs
        ],
    )

