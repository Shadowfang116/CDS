"""Case controls API endpoint for P9."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document, CaseDossierField
from app.schemas.controls import (
    CaseControlsResponse,
    RegimeInfo,
    PlaybookInfo,
    EvidenceChecklistItem,
    ProvidedDocument,
    CaseRiskInfo,
    ReadinessInfo,
)
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.services.regime_classifier import classify_regime, normalize_regime
from app.services.playbooks import get_active_playbooks, get_required_evidence
from app.services.approvals import compute_case_risk_score, get_case_readiness
from app.core.regimes import Regime

router = APIRouter(prefix="/cases", tags=["case-controls"])


@router.get("/{case_id}/controls", response_model=CaseControlsResponse)
async def get_case_controls(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get case controls: regime, playbooks, evidence checklist, risk, readiness.
    Single source of truth for case controls view.
    """
    # Load case (org-scoped)
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.org_id == current_user.org_id,  # Tenant isolation
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Determine regime
    regime_field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == current_user.org_id,
        CaseDossierField.field_key == "property.regime",
    ).first()
    
    regime_value = None
    confidence = 0.0
    reasons = []
    
    if regime_field and regime_field.field_value:
        # Use existing regime from dossier
        regime_value = normalize_regime(regime_field.field_value)
        if regime_value and regime_value != Regime.UNKNOWN:
            confidence = 0.9
            reasons = ["dossier_field"]
        else:
            regime_value = None
    
    if not regime_value or regime_value == Regime.UNKNOWN:
        # Run classifier
        regime_value, confidence, reasons = classify_regime(
            db, case_id, current_user.org_id, overwrite=False
        )
        # Optionally write back if absent (but don't overwrite existing)
        if not regime_field and regime_value and regime_value != Regime.UNKNOWN:
            new_field = CaseDossierField(
                org_id=current_user.org_id,
                case_id=case_id,
                field_key="property.regime",
                field_value=regime_value.value if regime_value else None,
                needs_confirmation=True,
            )
            db.add(new_field)
            db.commit()
    
    regime_str = regime_value.value if regime_value and regime_value != Regime.UNKNOWN else "UNKNOWN"
    
    # Apply playbooks for regime
    active_playbooks_data = get_active_playbooks(regime_str)
    playbooks = []
    for pb_data in active_playbooks_data:
        playbooks.append(PlaybookInfo(
            id=pb_data.get("id", ""),
            label=pb_data.get("label", ""),
            regimes=pb_data.get("regimes", []),
            rulesets=pb_data.get("rulesets", []),
            hard_stops=pb_data.get("hard_stops", []),
            required_evidence=pb_data.get("required_evidence", []),
        ))
    
    # Build evidence checklist
    all_required_evidence = get_required_evidence(active_playbooks_data)
    
    # Get all documents for this case
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).all()
    
    evidence_checklist = []
    for ev_item in all_required_evidence:
        code = ev_item.get("code", "")
        label = ev_item.get("label", "")
        acceptable_doc_types = ev_item.get("acceptable_doc_types", [])
        
        # Find matching documents
        provided_docs = []
        for doc in documents:
            if doc.doc_type and doc.doc_type.lower() in [dt.lower() for dt in acceptable_doc_types]:
                provided_docs.append(ProvidedDocument(
                    document_id=doc.id,
                    filename=doc.original_filename or "",
                    doc_type=doc.doc_type,
                    page_count=doc.page_count,
                ))
        
        status_str = "Provided" if provided_docs else "Missing"
        
        evidence_checklist.append(EvidenceChecklistItem(
            code=code,
            label=label,
            acceptable_doc_types=acceptable_doc_types,
            provided_documents=provided_docs,
            status=status_str,
        ))
    
    # Compute risk
    risk_data = compute_case_risk_score(db, current_user.org_id, case_id)
    risk = CaseRiskInfo(
        score=risk_data["score"],
        label=risk_data["label"],
        open_counts={
            "high": risk_data["high_count"],
            "medium": risk_data["medium_count"],
            "low": risk_data["low_count"],
            "hard_stop": risk_data["hard_stop_count"],
        },
    )
    
    # Compute readiness
    readiness_data = get_case_readiness(db, case_id, current_user.org_id)
    readiness = ReadinessInfo(
        ready=readiness_data["ready"],
        blocked_reasons=readiness_data.get("reasons", []),
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="controls.view",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "regime": regime_str,
            "playbook_count": len(playbooks),
            "evidence_items": len(evidence_checklist),
            "risk_label": risk.label,
            "readiness": readiness.ready,
        },
    )
    
    return CaseControlsResponse(
        case_id=case_id,
        regime=RegimeInfo(
            regime=regime_str,
            confidence=confidence,
            reasons=reasons,
        ),
        playbooks=playbooks,
        evidence_checklist=evidence_checklist,
        risk=risk,
        readiness=readiness,
    )

