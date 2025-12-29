"""Rule Engine v1 - Evaluates cases against YAML rulepack."""
import uuid
import re
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import yaml

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun
from app.models.verification import Verification

logger = logging.getLogger(__name__)

# Path to rulepack YAML - mounted from docs folder
RULEPACK_PATH = os.environ.get("RULEPACK_PATH", "/app/docs/05_rulepack_v1.yaml")


@dataclass
class EvidenceRef:
    """Reference to evidence in a document."""
    document_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    note: Optional[str] = None


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""
    rule_id: str
    module: str
    severity: str
    triggered: bool
    title: str = ""
    description: str = ""
    cp_text: str = ""
    evidence_required: str = ""
    resolution_conditions: str = ""
    evidence_refs: List[EvidenceRef] = field(default_factory=list)


@dataclass 
class CaseContext:
    """Normalized case data for rule evaluation."""
    org_id: uuid.UUID
    case_id: uuid.UUID
    dossier: Dict[str, List[str]]  # field_key -> list of values
    doc_types: List[str]  # list of doc_type values present
    doc_filenames: List[str]  # list of original filenames
    documents: List[Document]  # full document objects
    pages: List[Tuple[uuid.UUID, int, str]]  # (doc_id, page_num, ocr_text)
    verifications: Dict[str, str] = field(default_factory=dict)  # verification_type -> status


def load_rulepack() -> Dict[str, Any]:
    """Load rulepack YAML. Reloads on each call in dev mode."""
    try:
        with open(RULEPACK_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Rulepack not found at {RULEPACK_PATH}")
        return {"rules": []}
    except Exception as e:
        logger.error(f"Failed to load rulepack: {e}")
        return {"rules": []}


def build_case_context(db: Session, org_id: uuid.UUID, case_id: uuid.UUID) -> CaseContext:
    """Build normalized case context from database."""
    # Get dossier fields
    dossier_rows = db.query(CaseDossierField).filter(
        CaseDossierField.case_id == case_id,
        CaseDossierField.org_id == org_id,
    ).all()
    
    dossier: Dict[str, List[str]] = {}
    for row in dossier_rows:
        if row.field_value:
            if row.field_key not in dossier:
                dossier[row.field_key] = []
            dossier[row.field_key].append(row.field_value)
    
    # Get documents
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.org_id == org_id,
    ).all()
    
    doc_types = []
    doc_filenames = []
    for doc in documents:
        if doc.doc_type:
            doc_types.append(doc.doc_type)
        doc_filenames.append(doc.original_filename)
    
    # Get pages with OCR text
    pages: List[Tuple[uuid.UUID, int, str]] = []
    for doc in documents:
        doc_pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id,
            DocumentPage.org_id == org_id,
            DocumentPage.ocr_status == "Done",
        ).all()
        for page in doc_pages:
            if page.ocr_text:
                pages.append((doc.id, page.page_number, page.ocr_text))
    
    # Get verifications
    verifications_data = db.query(Verification).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
    ).all()
    verifications = {v.verification_type: v.status for v in verifications_data}
    
    return CaseContext(
        org_id=org_id,
        case_id=case_id,
        dossier=dossier,
        doc_types=doc_types,
        doc_filenames=doc_filenames,
        documents=documents,
        pages=pages,
        verifications=verifications,
    )


def normalize_cnic(cnic: str) -> str:
    """Normalize CNIC by removing formatting."""
    return re.sub(r'[^0-9]', '', cnic)


def infer_doc_type_from_filename(filename: str) -> Optional[str]:
    """Infer document type from filename using heuristics."""
    filename_lower = filename.lower()
    
    type_patterns = [
        (["cnic", "nic", "id card"], "CNIC Copy"),
        (["photo", "photograph", "passport"], "Photograph"),
        (["salary", "payslip", "pay slip"], "Salary Slip"),
        (["bank statement", "statement"], "Bank Statement"),
        (["utility", "electricity", "gas bill", "water bill"], "Utility Bill"),
        (["noc", "no objection"], "Society NOC"),
        (["allotment", "allocation"], "Allotment Letter"),
        (["possession", "handover"], "Possession Letter"),
        (["site", "verification", "inspection"], "Site Report"),
        (["resolution", "board"], "Board Resolution"),
        (["poa", "power of attorney"], "Power of Attorney"),
        (["plan", "layout", "building plan"], "Building Plan"),
    ]
    
    for patterns, doc_type in type_patterns:
        if any(p in filename_lower for p in patterns):
            return doc_type
    
    return None


def get_effective_doc_types(ctx: CaseContext) -> List[str]:
    """Get all doc types including inferred ones from filenames."""
    types = list(ctx.doc_types)
    
    # Infer types from filenames for documents without explicit type
    for doc in ctx.documents:
        if not doc.doc_type:
            inferred = infer_doc_type_from_filename(doc.original_filename)
            if inferred and inferred not in types:
                types.append(inferred)
    
    return types


# ============================================================
# EVALUATORS
# ============================================================

def evaluate_missing_evidence(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Check if required document types are missing."""
    required_types = rule.get("logic", {}).get("required_doc_types", [])
    effective_types = get_effective_doc_types(ctx)
    
    # Check if any required type is present (case-insensitive)
    effective_lower = [t.lower() for t in effective_types]
    found = False
    for req in required_types:
        if req.lower() in effective_lower:
            found = True
            break
        # Also check partial matches
        for eff in effective_lower:
            if req.lower() in eff or eff in req.lower():
                found = True
                break
        if found:
            break
    
    triggered = not found
    
    outputs = rule.get("outputs", {})
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=outputs.get("exception", ""),
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
    )


def evaluate_mismatch(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Check for mismatched values in dossier fields."""
    field_pattern = rule.get("logic", {}).get("field_pattern", "")
    
    # Collect all values for matching fields
    values = []
    for key, vals in ctx.dossier.items():
        if field_pattern in key:
            values.extend(vals)
    
    # Normalize and compare (for CNIC, remove formatting)
    if "cnic" in field_pattern.lower():
        normalized = [normalize_cnic(v) for v in values]
        unique = set(normalized)
        triggered = len(unique) > 1
    else:
        triggered = len(set(values)) > 1
    
    outputs = rule.get("outputs", {})
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=outputs.get("exception", ""),
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
    )


def evaluate_keyword_risk(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Search OCR text for risk keywords."""
    keywords = rule.get("logic", {}).get("keywords_any", [])
    if not keywords:
        keywords = rule.get("inputs", {}).get("keywords", [])
    
    triggered = False
    evidence_refs: List[EvidenceRef] = []
    found_keywords = set()
    
    for doc_id, page_num, ocr_text in ctx.pages:
        text_lower = ocr_text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                triggered = True
                found_keywords.add(kw)
                # Add evidence reference for first occurrence of this keyword
                if not any(r.document_id == doc_id and r.page_number == page_num for r in evidence_refs):
                    evidence_refs.append(EvidenceRef(
                        document_id=doc_id,
                        page_number=page_num,
                        note=f"Contains keyword: {kw}",
                    ))
    
    outputs = rule.get("outputs", {})
    description = outputs.get("exception", "")
    if found_keywords:
        description += f" (Keywords found: {', '.join(found_keywords)})"
    
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=description,
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
        evidence_refs=evidence_refs,
    )


def evaluate_timeline_gap(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Check for date/timeline inconsistencies."""
    # For MVP, this uses keyword-based detection
    # Full date parsing implementation would require more complex logic
    
    date_keywords = rule.get("logic", {}).get("date_keywords", [
        "before", "after", "prior to", "following", "preceded by"
    ])
    
    triggered = False
    evidence_refs: List[EvidenceRef] = []
    
    for doc_id, page_num, ocr_text in ctx.pages:
        text_lower = ocr_text.lower()
        for kw in date_keywords:
            if kw.lower() in text_lower:
                # This is a simplified check - real implementation would parse dates
                triggered = False  # Don't trigger on just keywords
                break
    
    outputs = rule.get("outputs", {})
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=outputs.get("exception", ""),
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
        evidence_refs=evidence_refs,
    )


def evaluate_verification_check(rule: Dict, ctx: CaseContext) -> RuleResult:
    """
    Check if verification is required and not yet completed.
    
    This evaluator checks for e-stamp or registry verification requirements.
    If the verification is already Verified, the rule does not trigger.
    """
    verification_type = rule.get("inputs", {}).get("verification_type", "")
    keywords = rule.get("inputs", {}).get("keywords", [])
    dossier_keys = rule.get("inputs", {}).get("dossier_keys", [])
    
    # Check if verification is already done
    verification_status = ctx.verifications.get(verification_type, "Pending")
    if verification_status == "Verified":
        # Already verified, don't trigger
        outputs = rule.get("outputs", {})
        return RuleResult(
            rule_id=rule["id"],
            module=rule["module"],
            severity=rule["severity"],
            triggered=False,
            title=outputs.get("title", ""),
            description=outputs.get("exception", ""),
            cp_text=outputs.get("cp", ""),
            evidence_required=outputs.get("evidence_required", ""),
            resolution_conditions=outputs.get("resolution_conditions", ""),
        )
    
    # Check if any dossier keys are present (indicating need for verification)
    has_keys = False
    for key in dossier_keys:
        for dossier_key in ctx.dossier.keys():
            if key in dossier_key:
                if ctx.dossier[dossier_key]:
                    has_keys = True
                    break
        if has_keys:
            break
    
    # Check if keywords are found in OCR (indicating relevant documents)
    has_keywords = False
    evidence_refs: List[EvidenceRef] = []
    
    for doc_id, page_num, ocr_text in ctx.pages:
        text_lower = ocr_text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                has_keywords = True
                evidence_refs.append(EvidenceRef(
                    document_id=doc_id,
                    page_number=page_num,
                    note=f"Contains keyword: {kw}",
                ))
                break
        if has_keywords:
            break
    
    # Trigger if we have keys or keywords but not verified
    triggered = has_keys or has_keywords
    
    outputs = rule.get("outputs", {})
    description = outputs.get("exception", "")
    if triggered and verification_status == "Failed":
        description += " (Previous verification attempt failed)"
    
    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=description,
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
        evidence_refs=evidence_refs,
    )


EVALUATORS = {
    "missing_evidence": evaluate_missing_evidence,
    "mismatch": evaluate_mismatch,
    "keyword_risk": evaluate_keyword_risk,
    "timeline_gap": evaluate_timeline_gap,
    "verification_check": evaluate_verification_check,
}


def evaluate_rule(rule: Dict, ctx: CaseContext) -> RuleResult:
    """Evaluate a single rule against case context."""
    evaluator_name = rule.get("evaluator", "missing_evidence")
    evaluator = EVALUATORS.get(evaluator_name, evaluate_missing_evidence)
    return evaluator(rule, ctx)


def run_rules(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Dict[str, int]:
    """
    Run all rules against a case, create exceptions and CPs.
    
    Returns summary counts.
    """
    started_at = datetime.utcnow()
    
    # Create rule run record
    rule_run = RuleRun(
        org_id=org_id,
        case_id=case_id,
        started_at=started_at,
    )
    db.add(rule_run)
    db.flush()
    
    # Build case context
    ctx = build_case_context(db, org_id, case_id)
    
    # Load rulepack
    rulepack = load_rulepack()
    rules = rulepack.get("rules", [])
    
    # Delete prior Open exceptions and CPs (keep Resolved/Waived)
    db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.org_id == org_id,
        ExceptionEvidenceRef.exception_id.in_(
            db.query(Exception_.id).filter(
                Exception_.case_id == case_id,
                Exception_.org_id == org_id,
                Exception_.status == "Open",
            )
        )
    ).delete(synchronize_session=False)
    
    db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status == "Open",
    ).delete(synchronize_session=False)
    
    db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.status == "Open",
    ).delete(synchronize_session=False)
    
    # Evaluate rules
    results: List[RuleResult] = []
    for rule in rules:
        try:
            result = evaluate_rule(rule, ctx)
            results.append(result)
        except Exception as e:
            logger.error(f"Rule {rule.get('id', 'unknown')} evaluation failed: {e}")
    
    # Create exceptions and CPs for triggered rules
    counts = {"high": 0, "medium": 0, "low": 0, "total": 0, "cps_total": 0}
    
    for result in results:
        if result.triggered:
            # Create exception
            exc = Exception_(
                org_id=org_id,
                case_id=case_id,
                rule_id=result.rule_id,
                module=result.module,
                severity=result.severity,
                title=result.title,
                description=result.description,
                cp_text=result.cp_text,
                resolution_conditions=result.resolution_conditions,
                status="Open",
            )
            db.add(exc)
            db.flush()
            
            # Create evidence refs
            for ref in result.evidence_refs:
                evidence_ref = ExceptionEvidenceRef(
                    org_id=org_id,
                    exception_id=exc.id,
                    document_id=ref.document_id,
                    page_number=ref.page_number,
                    note=ref.note,
                )
                db.add(evidence_ref)
            
            # Create CP if cp_text provided
            if result.cp_text:
                cp = ConditionPrecedent(
                    org_id=org_id,
                    case_id=case_id,
                    rule_id=result.rule_id,
                    severity=result.severity,
                    text=result.cp_text,
                    evidence_required=result.evidence_required,
                    status="Open",
                )
                db.add(cp)
                counts["cps_total"] += 1
            
            # Update counts
            severity_lower = result.severity.lower()
            if severity_lower in counts:
                counts[severity_lower] += 1
            counts["total"] += 1
    
    # Update rule run
    rule_run.finished_at = datetime.utcnow()
    rule_run.summary = counts
    
    db.commit()
    
    return counts

