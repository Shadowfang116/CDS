"""Matter workbench read model and thin product façades.

Does not replace existing routes. Workbench GET aggregates CORE services.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.approval import ApprovalRequest
from app.models.case import Case
from app.models.document import CaseDossierField, Document
from app.models.export import Export
from app.models.rules import ConditionPrecedent, Exception_
from app.models.user import User
from app.models.verification import Verification
from app.services.approvals import create_approval_request, get_case_readiness
from app.services.dossier_autofill import autofill_dossier
from app.services.exception_waive import exception_is_waivable
from app.services.next_action import rank_next_action
from app.services.rule_engine import run_rules
from app.services.workflow import normalize_case_status, transition_case


KYC_NOISE = ("salary", "photograph", "photo", "utility", "co-applicant")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def finding_view_from_exception(item: Exception_) -> dict[str, Any]:
    refs = item.evidence_refs if isinstance(item.evidence_refs, list) else []
    return {
        "kind": "exception",
        "id": str(item.id),
        "rule_id": item.rule_id,
        "module": item.module,
        "severity": item.severity,
        "status": item.status,
        "title": item.title,
        "description": item.description,
        "cp_text": item.cp_text,
        "resolution_conditions": item.resolution_conditions,
        "evidence_refs": refs,
        "hard_stop": bool(item.is_hard_stop),
        "is_hard_stop": bool(item.is_hard_stop),
        "waivable": exception_is_waivable(item),
        "waiver_reason": item.waiver_reason,
        "waiver_state": "Waived" if item.status == "Waived" else "Open",
        "source_document_id": str(item.source_document_id) if item.source_document_id else None,
        "source_page": item.source_page,
    }


def finding_view_from_cp(item: ConditionPrecedent) -> dict[str, Any]:
    status = "Met" if item.status == "Satisfied" else item.status
    return {
        "kind": "cp",
        "id": str(item.id),
        "rule_id": item.rule_id,
        "module": None,
        "severity": item.severity or "High",
        "status": status,
        "title": item.text,
        "description": None,
        "cp_text": item.text,
        "resolution_conditions": item.evidence_required,
        "evidence_refs": [],
        "hard_stop": False,
        "is_hard_stop": False,
        "waivable": True,
        "waiver_reason": item.waiver_reason,
        "waiver_state": status,
        "source_document_id": None,
        "source_page": None,
    }


def serialize_document(doc: Document) -> dict[str, Any]:
    return {
        "id": str(doc.id),
        "original_filename": doc.original_filename,
        "page_count": doc.page_count,
        "status": doc.status,
        "error_message": doc.error_message,
        "doc_type": doc.doc_type,
        "predicted_doc_type": doc.predicted_doc_type,
        "corrected_doc_type": doc.corrected_doc_type,
        "classification_confidence": float(doc.classification_confidence) if doc.classification_confidence is not None else None,
        "classification_status": doc.classification_status,
        "needs_review": bool(doc.needs_review),
        "created_at": _iso(doc.created_at),
        "updated_at": _iso(doc.updated_at),
    }


def _is_kyc_noise(label: str | None) -> bool:
    text = (label or "").lower()
    return any(token in text for token in KYC_NOISE)


def compute_next_action(
    *,
    findings: list[dict[str, Any]],
    fields: list[CaseDossierField],
    verifications: list[Verification],
    status: str,
) -> str:
    open_findings = [item for item in findings if item.get("status") == "Open"]
    hard = next((item for item in open_findings if item.get("hard_stop")), None)
    high = next((item for item in open_findings if item.get("kind") == "exception" and item.get("severity") == "High"), None)
    cp = next((item for item in open_findings if item.get("kind") == "cp"), None)
    medium = next((item for item in open_findings if item.get("severity") == "Medium"), None)
    low = next((item for item in open_findings if item.get("severity") == "Low"), None)
    unconfirmed = next((item for item in fields if getattr(item, "needs_confirmation", False)), None)
    pending_ver = next((item for item in verifications if item.status == "Pending"), None)
    missing = None
    if high and high.get("resolution_conditions") and not _is_kyc_noise(high.get("title")):
        missing = high.get("resolution_conditions")
    return rank_next_action(
        open_hard_stop_title=hard.get("title") if hard else None,
        missing_required_causing_high=missing,
        unconfirmed_key_field=unconfirmed.field_key if unconfirmed else None,
        open_high_title=high.get("title") if high else None,
        blocking_cp_text=cp.get("title") if cp else None,
        pending_verification=getattr(pending_ver, "verification_type", None) if pending_ver else None,
        open_medium_title=medium.get("title") if medium else None,
        open_low_title=low.get("title") if low else None,
        pack_hint="Issue bank pack" if status == "Approved" else "Submit for approval",
    )


def get_workbench(db: Session, *, org_id: uuid.UUID, case_id: uuid.UUID) -> dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    documents = (
        db.query(Document)
        .filter(Document.case_id == case_id, Document.org_id == org_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    exceptions = (
        db.query(Exception_)
        .filter(Exception_.case_id == case_id, Exception_.org_id == org_id)
        .order_by(Exception_.created_at.desc())
        .all()
    )
    cps = (
        db.query(ConditionPrecedent)
        .filter(ConditionPrecedent.case_id == case_id, ConditionPrecedent.org_id == org_id)
        .order_by(ConditionPrecedent.created_at.desc())
        .all()
    )
    findings = [finding_view_from_exception(item) for item in exceptions] + [
        finding_view_from_cp(item) for item in cps
    ]
    fields = (
        db.query(CaseDossierField)
        .filter(CaseDossierField.case_id == case_id, CaseDossierField.org_id == org_id)
        .all()
    )
    verifications = (
        db.query(Verification)
        .filter(Verification.case_id == case_id, Verification.org_id == org_id)
        .all()
    )
    approvals = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.case_id == case_id,
            ApprovalRequest.org_id == org_id,
            ApprovalRequest.status == "Pending",
        )
        .order_by(ApprovalRequest.created_at.desc())
        .all()
    )
    user_ids = {row.requested_by_user_id for row in approvals}
    users = {row.id: row.email for row in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    exports = (
        db.query(Export)
        .filter(Export.case_id == case_id, Export.org_id == org_id)
        .order_by(Export.created_at.desc())
        .all()
    )
    readiness_raw = get_case_readiness(db, case_id=case_id, org_id=org_id)
    readiness = {
        "case_id": str(case_id),
        "ready": bool(readiness_raw.get("ready")),
        "reasons": readiness_raw.get("reasons") or [],
        "metrics": readiness_raw.get("metrics") or {},
    }
    confirmed = sum(1 for item in fields if not getattr(item, "needs_confirmation", False) and item.field_value)
    unconfirmed = sum(1 for item in fields if getattr(item, "needs_confirmation", False))

    return {
        "matter": {
            "id": str(case.id),
            "org_id": str(case.org_id),
            "title": case.title,
            "status": case.status,
            "decision": case.decision,
            "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
            "created_at": _iso(case.created_at),
            "updated_at": _iso(case.updated_at),
        },
        "lifecycle_status": case.status,
        "decision": case.decision,
        "readiness": readiness,
        "next_action": compute_next_action(
            findings=findings,
            fields=fields,
            verifications=verifications,
            status=case.status,
        ),
        "documents": [serialize_document(doc) for doc in documents],
        "dossier_progress": {
            "field_count": len(fields),
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
        },
        "fields": [
            {
                "field_key": item.field_key,
                "field_value": item.field_value,
                "needs_confirmation": bool(getattr(item, "needs_confirmation", False)),
            }
            for item in fields
        ],
        "findings": findings,
        "pending_approvals": [
            {
                "id": str(row.id),
                "case_id": str(row.case_id),
                "requested_by_user_id": str(row.requested_by_user_id),
                "requested_by_email": users.get(row.requested_by_user_id),
                "requested_by_role": row.requested_by_role,
                "request_type": row.request_type,
                "request_type_label": row.request_type,
                "status": row.status,
                "payload_json": row.payload_json or {},
                "created_at": _iso(row.created_at),
                "updated_at": _iso(row.updated_at),
            }
            for row in approvals
        ],
        "exports": [
            {
                "id": str(row.id),
                "filename": row.filename,
                "status": row.status,
                "export_type": row.export_type,
            }
            for row in exports
        ],
        "verifications": [
            {
                "id": str(row.id),
                "status": row.status,
                "verification_type": getattr(row, "verification_type", None) or getattr(row, "type", None),
            }
            for row in verifications
        ],
    }


def process_document(db: Session, *, document: Document, org_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    from app.services.ocr_enqueue import enqueue_ocr_for_document

    return enqueue_ocr_for_document(db, document=document, org_id=org_id, user_id=user_id)


def extract_facts(db: Session, *, org_id: uuid.UUID, case_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    result = autofill_dossier(db=db, org_id=org_id, case_id=case_id, user_id=user_id, overwrite=False)
    extracted = []
    for item in result.get("extracted") or []:
        extracted.append(
            {
                "field_path": getattr(item, "field_path", None),
                "value": getattr(item, "value", None),
                "confidence": getattr(item, "confidence", None),
                "evidence": getattr(item, "evidence", None) or {},
            }
        )
    return {
        "case_id": str(case_id),
        "overwrite": False,
        "extracted": extracted,
        "updated_fields": result.get("updated_fields") or [],
        "skipped_fields": result.get("skipped_fields") or [],
        "errors": result.get("errors") or [],
    }


def confirm_fact(
    db: Session,
    *,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    field_key: str,
    user_id: uuid.UUID,
) -> CaseDossierField:
    field = (
        db.query(CaseDossierField)
        .filter(
            CaseDossierField.org_id == org_id,
            CaseDossierField.case_id == case_id,
            CaseDossierField.field_key == field_key,
        )
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Dossier field not found")
    field.needs_confirmation = False
    field.confirmed_by_user_id = user_id
    field.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(field)
    return field


def evaluate_matter(db: Session, *, org_id: uuid.UUID, case_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    result = run_rules(db, org_id, case_id, user_id)
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if case:
        from app.services.resolution import reconcile_case_progress
        reconcile_case_progress(db, case=case)
        db.commit()
    return result


def request_waiver(
    db: Session,
    *,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    exception_id: str,
    waiver_reason: str,
) -> ApprovalRequest:
    return create_approval_request(
        db,
        org_id=org_id,
        case_id=case_id,
        requested_by_user_id=user_id,
        requested_by_role=role,
        request_type="exception_waive",
        payload={"exception_id": exception_id, "waiver_reason": waiver_reason},
    )


def submit_matter(
    db: Session,
    *,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    decision: str,
    rationale: str,
) -> ApprovalRequest:
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    current = normalize_case_status(case.status)
    if current in {"Processing", "Pending Docs"}:
        transition_case(db, case=case, next_status="Review")
    if normalize_case_status(case.status) != "Ready for Approval":
        transition_case(db, case=case, next_status="Ready for Approval")
    db.commit()
    return create_approval_request(
        db,
        org_id=org_id,
        case_id=case_id,
        requested_by_user_id=user_id,
        requested_by_role=role,
        request_type="case_decision",
        payload={"decision": decision, "rationale": rationale},
    )
