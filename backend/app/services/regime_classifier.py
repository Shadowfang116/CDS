"""Regime classifier service for inferring property jurisdiction."""
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.regimes import Regime, normalize_regime
from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.case import Case

logger = logging.getLogger(__name__)


def classify_regime(
    db: Session,
    case_id: uuid.UUID,
    org_id: uuid.UUID,
    overwrite: bool = False,
) -> Tuple[Optional[Regime], float, List[str]]:
    """
    Classify regime for a case based on dossier fields, document types, and OCR keywords.
    
    Returns:
        (regime, confidence, reasons)
    """
    reasons: List[str] = []
    confidence = 0.0
    
    # Check if regime already exists
    existing_regime_field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
        CaseDossierField.field_key == "property.regime",
    ).first()
    
    if existing_regime_field and not overwrite:
        existing_regime = normalize_regime(existing_regime_field.field_value)
        if existing_regime and existing_regime != Regime.UNKNOWN:
            return existing_regime, 0.9, ["existing_dossier_field"]
    
    # Get dossier fields
    dossier_fields = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
    ).all()
    dossier_dict = {f.field_key: f.field_value for f in dossier_fields}
    
    # Get documents and OCR text
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).all()
    
    # Collect OCR text from Done pages
    ocr_texts: List[str] = []
    doc_types: List[str] = []
    filenames: List[str] = []
    
    for doc in documents:
        if doc.doc_type:
            doc_types.append(doc.doc_type.lower())
        if doc.original_filename:
            filenames.append(doc.original_filename.lower())
        
        pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id,
            DocumentPage.org_id == org_id,
            DocumentPage.ocr_status == "Done",
        ).all()
        
        for page in pages:
            if page.ocr_text:
                ocr_texts.append(page.ocr_text.lower())
    
    # Combine all OCR text
    combined_ocr = " ".join(ocr_texts).lower()
    
    # Heuristics (ordered by specificity)
    regime_scores: Dict[Regime, float] = {}
    
    # DHA detection
    if any("dha" in dt for dt in doc_types) or any("dha" in fn for fn in filenames):
        regime_scores[Regime.DHA] = 0.9
        reasons.append("doc_type:dha_*")
    if "dha" in combined_ocr or "defence housing" in combined_ocr:
        regime_scores[Regime.DHA] = max(regime_scores.get(Regime.DHA, 0.0), 0.8)
        reasons.append("keyword:DHA")
    
    # LDA detection
    if any("lda" in dt for dt in doc_types) or any("lda" in fn for fn in filenames):
        regime_scores[Regime.LDA] = 0.9
        reasons.append("doc_type:lda_*")
    if "lda" in combined_ocr or "lahore development" in combined_ocr or "placement letter" in combined_ocr:
        regime_scores[Regime.LDA] = max(regime_scores.get(Regime.LDA, 0.0), 0.8)
        reasons.append("keyword:LDA")
    
    # RUDA detection
    if any("ruda" in dt for dt in doc_types) or any("ruda" in fn for fn in filenames):
        regime_scores[Regime.RUDA] = 0.9
        reasons.append("doc_type:ruda_*")
    if "ruda" in combined_ocr or "ravi urban" in combined_ocr:
        regime_scores[Regime.RUDA] = max(regime_scores.get(Regime.RUDA, 0.0), 0.8)
        reasons.append("keyword:RUDA")
    
    # Cantonment detection
    if "cantonment board" in combined_ocr or "cb " in combined_ocr or "leasehold" in combined_ocr:
        regime_scores[Regime.CANTONMENT] = 0.8
        reasons.append("keyword:Cantonment")
    if any("cantonment" in dt for dt in doc_types) or any("cantonment" in fn for fn in filenames):
        regime_scores[Regime.CANTONMENT] = max(regime_scores.get(Regime.CANTONMENT, 0.0), 0.9)
        reasons.append("doc_type:cantonment_*")
    
    # Society detection
    if any("society" in dt for dt in doc_types) or "society_transfer" in doc_types or "society_allotment" in doc_types:
        regime_scores[Regime.SOCIETY] = 0.9
        reasons.append("doc_type:society_*")
    if "society" in combined_ocr or "membership" in combined_ocr or "allotment" in combined_ocr:
        regime_scores[Regime.SOCIETY] = max(regime_scores.get(Regime.SOCIETY, 0.0), 0.7)
        reasons.append("keyword:Society")
    
    # Revenue detection
    if "fard" in combined_ocr or "jamabandi" in combined_ocr or "khasra" in combined_ocr or "khewat" in combined_ocr or "mouza" in combined_ocr:
        regime_scores[Regime.REVENUE] = 0.8
        reasons.append("keyword:Revenue")
    if any("fard" in dt for dt in doc_types) or "jamabandi" in doc_types or "mutation" in doc_types:
        regime_scores[Regime.REVENUE] = max(regime_scores.get(Regime.REVENUE, 0.0), 0.9)
        reasons.append("doc_type:revenue_*")
    
    # Municipal detection
    if "municipal" in combined_ocr or "tma" in combined_ocr or "mc " in combined_ocr or "property tax" in combined_ocr or "pt-1" in combined_ocr:
        regime_scores[Regime.MUNICIPAL] = 0.7
        reasons.append("keyword:Municipal")
    
    # Check dossier fields
    scheme_name = dossier_dict.get("property.scheme_name", "").lower()
    if "dha" in scheme_name:
        regime_scores[Regime.DHA] = max(regime_scores.get(Regime.DHA, 0.0), 0.85)
        reasons.append("dossier:scheme_name")
    if "lda" in scheme_name:
        regime_scores[Regime.LDA] = max(regime_scores.get(Regime.LDA, 0.0), 0.85)
        reasons.append("dossier:scheme_name")
    
    # Select highest scoring regime
    if regime_scores:
        best_regime = max(regime_scores.items(), key=lambda x: x[1])
        confidence = best_regime[1]
        return best_regime[0], confidence, reasons
    
    # Default to UNKNOWN
    return Regime.UNKNOWN, 0.0, ["no_indicators_found"]


def infer_and_store_regime(
    db: Session,
    case_id: uuid.UUID,
    org_id: uuid.UUID,
    overwrite: bool = False,
) -> Tuple[Optional[Regime], float, List[str]]:
    """
    Infer regime and store in dossier field.
    
    Returns:
        (regime, confidence, reasons)
    """
    regime, confidence, reasons = classify_regime(db, case_id, org_id, overwrite)
    
    # Store in dossier
    existing_field = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
        CaseDossierField.field_key == "property.regime",
    ).first()
    
    if existing_field:
        if overwrite or not existing_field.field_value:
            existing_field.field_value = regime.value if regime else None
            case_row = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
            existing_field.updated_at = case_row.updated_at if case_row else None
    else:
        from datetime import datetime
        new_field = CaseDossierField(
            org_id=org_id,
            case_id=case_id,
            field_key="property.regime",
            field_value=regime.value if regime else None,
            needs_confirmation=True,
            source_document_id=None,
            source_page_number=None,
        )
        db.add(new_field)
    
    db.commit()
    
    # Audit log
    from app.services.audit import write_audit_event
    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=None,  # System action
        action="dossier.regime_inferred",
        entity_type="case",
        entity_id=case_id,
        event_metadata={
            "regime": regime.value if regime else None,
            "confidence": confidence,
            "reasons": reasons,
        },
    )
    
    return regime, confidence, reasons

