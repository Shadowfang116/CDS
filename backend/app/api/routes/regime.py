"""Regime classification API endpoints."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.case import Case
from app.api.deps import get_current_user, CurrentUser, require_roles
from app.services.regime_classifier import infer_and_store_regime
from app.services.audit import write_audit_event
from app.core.regimes import Regime

router = APIRouter(tags=["regime"])


class RegimeInferenceResponse(BaseModel):
    regime: str
    confidence: float
    reasons: list[str]
    authority_name: str | None = None


@router.post("/cases/{case_id}/regime/infer", response_model=RegimeInferenceResponse)
async def infer_regime(
    request: Request,
    case_id: uuid.UUID,
    overwrite: bool = Query(False, description="Overwrite existing regime"),
    current_user: CurrentUser = Depends(require_roles("Admin", "Reviewer")),
    db: Session = Depends(get_db),
):
    """Infer and store regime for a case."""
    # Verify case exists and belongs to org
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Infer regime
    regime, confidence, reasons = infer_and_store_regime(
        db=db,
        case_id=case_id,
        org_id=current_user.org_id,
        overwrite=overwrite,
    )
    
    # Get authority name from dossier
    from app.models.document import CaseDossierField
    authority_field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == "property.authority_name",
    ).first()
    
    authority_name = authority_field.field_value if authority_field else None
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="regime.inferred",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "regime": regime.value if regime else None,
            "confidence": confidence,
            "reasons": reasons,
            "overwrite": overwrite,
        },
    )
    
    return RegimeInferenceResponse(
        regime=regime.value if regime else Regime.UNKNOWN.value,
        confidence=confidence,
        reasons=reasons,
        authority_name=authority_name,
    )

