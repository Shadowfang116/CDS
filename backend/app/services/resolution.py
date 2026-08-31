"""Shared exception-resolution progress rules."""
from __future__ import annotations

from typing import Iterable, Any
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.roles import role_satisfies
from app.models.case import Case
from app.models.cp_evidence import CPEvidenceRef
from app.models.rules import ConditionPrecedent, Exception_, ExceptionEvidenceRef
from app.services.rule_engine import compute_case_decision
from app.services.workflow import normalize_case_status, transition_case


def compute_reconciled_decision(exceptions: Iterable[Any], cps: Iterable[Any]) -> str:
    """Compute the live case decision after a finding transition."""
    cp_rows = list(cps)
    open_cps = sum(1 for cp in cp_rows if getattr(cp, "status", "Open") == "Open")
    return compute_case_decision(list(exceptions), open_material_cps=open_cps)


def lifecycle_status_after_reconcile(status: str, *, ready: bool, decision: str) -> str:
    """Return the next safe lifecycle status after progress is reconciled."""
    normalized = (status or "New").strip()
    if normalized in {"Approved", "Rejected", "Closed"}:
        return normalized
    if normalized == "New":
        return "Processing"
    if normalized == "Processing":
        return "Review"
    if normalized == "Review" and ready and decision != "FAIL":
        return "Ready for Approval"
    if normalized == "Ready for Approval" and (not ready or decision == "FAIL"):
        return "Review"
    return normalized


def _linked_cps(db: Session, exception_item: Exception_) -> list[ConditionPrecedent]:
    """Find generated CPs for an exception, with rule-key fallback for old rows."""
    query = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.org_id == exception_item.org_id,
        ConditionPrecedent.case_id == exception_item.case_id,
    )
    linked = query.filter(ConditionPrecedent.source_exception_id == exception_item.id).all()
    if linked or not exception_item.rule_id:
        return linked
    return query.filter(ConditionPrecedent.rule_id == exception_item.rule_id).all()


def _validate_closing_refs(
    db: Session,
    *,
    exception_item: Exception_,
    closing_evidence_ref_ids: Iterable[str],
) -> list[ExceptionEvidenceRef]:
    ids = [uuid.UUID(str(value)) for value in closing_evidence_ref_ids]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="closing_evidence_ref_ids must not contain duplicates")
    if not ids:
        return []
    refs = db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.org_id == exception_item.org_id,
        ExceptionEvidenceRef.exception_id == exception_item.id,
        ExceptionEvidenceRef.id.in_(ids),
    ).all()
    if len(refs) != len(ids):
        raise HTTPException(status_code=422, detail="Every closing evidence reference must belong to this exception")
    if any(not ref.is_closing for ref in refs):
        raise HTTPException(status_code=422, detail="Evidence must be linked as closing proof before resolution")
    return refs


def _advance_case_status(db: Session, case: Case, *, decision: str, ready: bool) -> tuple[str, str]:
    before = normalize_case_status(case.status)
    current = before
    if current in {"Approved", "Rejected", "Closed"}:
        return before, current

    # Existing evaluated matters can be left at New; bring them through the
    # same legal lifecycle in order instead of skipping directly to approval.
    if current == "New":
        transition_case(db, case=case, next_status="Processing")
        current = normalize_case_status(case.status)
    if current == "Processing":
        transition_case(db, case=case, next_status="Review")
        current = normalize_case_status(case.status)
    if current == "Review" and ready and decision != "FAIL":
        transition_case(db, case=case, next_status="Ready for Approval")
        current = normalize_case_status(case.status)
    elif current == "Ready for Approval" and (not ready or decision == "FAIL"):
        transition_case(db, case=case, next_status="Review")
        current = normalize_case_status(case.status)
    return before, current


def reconcile_case_progress(
    db: Session,
    *,
    case: Case,
    advance_status: bool = True,
) -> dict[str, Any]:
    """Recompute decision/readiness and safely advance or retreat lifecycle."""
    exceptions = db.query(Exception_).filter(
        Exception_.case_id == case.id,
        Exception_.org_id == case.org_id,
    ).all()
    cps = db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case.id,
        ConditionPrecedent.org_id == case.org_id,
    ).all()
    decision = compute_reconciled_decision(exceptions, cps)
    case.decision = decision

    if advance_status:
        # Readiness needs Review/Ready status. Treat any evaluated finding set
        # as enough evidence to move stale New/Processing records forward.
        if exceptions or cps:
            if normalize_case_status(case.status) == "New":
                transition_case(db, case=case, next_status="Processing")
            if normalize_case_status(case.status) == "Processing":
                transition_case(db, case=case, next_status="Review")

    from app.services.approvals import get_case_readiness

    readiness = get_case_readiness(db, case_id=case.id, org_id=case.org_id)
    ready = bool(readiness.get("ready")) and decision != "FAIL"
    before_status = normalize_case_status(case.status)
    if advance_status:
        if before_status == "Review" and ready:
            transition_case(db, case=case, next_status="Ready for Approval")
        elif before_status == "Ready for Approval" and not ready:
            transition_case(db, case=case, next_status="Review")

    open_items = [item for item in exceptions if getattr(item, "status", "Open") == "Open"]
    hard_stop = next((item.title for item in open_items if getattr(item, "is_hard_stop", False)), None)
    high = next((item.title for item in open_items if getattr(item, "severity", "") == "High"), None)
    medium = next((item.title for item in open_items if getattr(item, "severity", "") == "Medium"), None)
    from app.services.next_action import rank_next_action
    next_action = rank_next_action(open_hard_stop_title=hard_stop, open_high_title=high, open_medium_title=medium)

    return {
        "decision": decision,
        "readiness": {
            "ready": ready,
            "reasons": readiness.get("reasons", []) if not ready else ["All criteria met"],
            "metrics": readiness.get("metrics", {}),
        },
        "status": normalize_case_status(case.status),
        "previous_status": before_status,
        "next_action": next_action,
    }


def resolve_exception(
    db: Session,
    *,
    exception_item: Exception_,
    user_id: uuid.UUID,
    role: str,
    reason: str,
    closing_evidence_ref_ids: Iterable[str],
) -> tuple[list[ConditionPrecedent], dict[str, Any]]:
    """Resolve an exception and generated CPs in one database transaction."""
    if not role_satisfies(role, "Reviewer"):
        raise HTTPException(status_code=403, detail="Reviewer role required to resolve or reopen exceptions")
    closure_reason = reason.strip()
    if not closure_reason:
        raise HTTPException(status_code=422, detail="reason is required when resolving an exception")
    if exception_item.status == "Waived":
        raise HTTPException(status_code=409, detail="Waived exception cannot be resolved")

    linked_cps = _linked_cps(db, exception_item)
    if exception_item.status == "Resolved":
        # Safe retry: already closed; do not require the original payload again.
        return linked_cps, reconcile_case_progress(db, case=_get_case(db, exception_item), advance_status=True)
    refs = _validate_closing_refs(
        db,
        exception_item=exception_item,
        closing_evidence_ref_ids=closing_evidence_ref_ids,
    )
    evidence_required = any(bool(cp.evidence_required) for cp in linked_cps if cp.status == "Open")
    if evidence_required and not refs:
        raise HTTPException(status_code=422, detail="Closing evidence is required before resolving this exception")

    now = datetime.utcnow()
    exception_item.status = "Resolved"
    exception_item.resolved_by_user_id = user_id
    exception_item.resolved_at = now
    exception_item.waiver_reason = None
    exception_item.waived_by_user_id = None
    exception_item.waived_at = None

    for cp in linked_cps:
        if cp.status != "Open":
            continue
        if exception_item.rule_id and cp.source_exception_id is None and cp.rule_id == exception_item.rule_id:
            cp.source_exception_id = exception_item.id
        cp.status = "Satisfied"
        cp.satisfied_at = now
        cp.satisfied_by_user_id = user_id
        cp.auto_satisfied_from_exception = True
        for ref in refs:
            exists = db.query(CPEvidenceRef).filter(
                CPEvidenceRef.org_id == cp.org_id,
                CPEvidenceRef.cp_id == cp.id,
                CPEvidenceRef.document_id == ref.document_id,
                CPEvidenceRef.page_number == ref.page_number,
            ).first()
            if not exists:
                db.add(CPEvidenceRef(
                    org_id=cp.org_id,
                    cp_id=cp.id,
                    document_id=ref.document_id,
                    page_number=ref.page_number,
                    note=ref.note,
                    created_by_user_id=user_id,
                ))

    progress = reconcile_case_progress(db, case=_get_case(db, exception_item), advance_status=True)
    db.flush()
    return linked_cps, progress


def _get_case(db: Session, exception_item: Exception_) -> Case:
    case = db.query(Case).filter(
        Case.id == exception_item.case_id,
        Case.org_id == exception_item.org_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
