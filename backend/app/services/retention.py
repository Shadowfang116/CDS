"""
Phase 9: Retention enforcement — delete Closed cases older than RETENTION_DAYS.
Deletion order: exports (+ MinIO) -> document pages / OCR -> documents (+ MinIO) -> exceptions/CPs/rules -> dossier -> case.
Idempotent; one audit event per deleted case.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.case import Case
from app.models.document import Document, DocumentPage, CaseDossierField
from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun
from app.models.cp_evidence import CPEvidenceRef
from app.models.export import Export
from app.models.verification import Verification, VerificationEvidenceRef
from app.models.approval import ApprovalRequest
from app.models.notification import Notification
from app.models.dossier_field_history import DossierFieldHistory
from app.models.ocr_extraction import OCRExtractionCandidate
from app.models.ocr_text_correction import OCRTextCorrection
from app.models.user import UserOrgRole
from botocore.exceptions import ClientError
from app.services.storage import delete_objects_by_prefix, get_s3_client
from app.services.audit import write_audit_event

REQUEST_ID_RETENTION = "retention-job"


def _get_actor_user_id_for_org(db: Session, org_id: uuid.UUID) -> Optional[uuid.UUID]:
    """Return first user_id in org (for system jobs like retention that need an audit actor)."""
    row = db.query(UserOrgRole.user_id).filter(UserOrgRole.org_id == org_id).limit(1).first()
    return row[0] if row else None


def _safe_delete_prefix(prefix: str) -> int:
    """Delete MinIO objects by prefix; ignore not found (idempotent)."""
    return delete_objects_by_prefix(prefix, ignore_not_found=True)


def run_retention_for_org(
    db: Session,
    org_id: uuid.UUID,
    actor_user_id: Optional[uuid.UUID] = None,
    retention_days: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Delete Closed cases older than retention_days. Returns counts and list of deleted case_ids.
    If dry_run=True, no deletes are performed; only counts of what would be deleted.
    If actor_user_id is None, uses first user in org for audit (required for retention.case_deleted).
    """
    days = retention_days if retention_days is not None else settings.RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)
    actor = actor_user_id or _get_actor_user_id_for_org(db, org_id)

    cases_to_delete = (
        db.query(Case)
        .filter(
            Case.org_id == org_id,
            Case.status == "Closed",
            Case.created_at < cutoff,
        )
        .all()
    )

    deleted_case_ids = []
    total_db_rows = 0
    total_minio_objects = 0

    for case in cases_to_delete:
        case_id = case.id
        org_id_val = case.org_id
        counts = {"exports": 0, "document_pages": 0, "documents": 0, "exceptions": 0, "cps": 0, "rule_runs": 0, "dossier_fields": 0, "other": 0}

        if dry_run:
            exports = db.query(Export).filter(Export.case_id == case_id, Export.org_id == org_id_val).count()
            counts["exports"] = exports
            doc_ids = [r[0] for r in db.query(Document.id).filter(Document.case_id == case_id, Document.org_id == org_id_val).all()]
            counts["documents"] = len(doc_ids)
            if doc_ids:
                counts["document_pages"] = db.query(DocumentPage).filter(DocumentPage.document_id.in_(doc_ids)).count()
            counts["exceptions"] = db.query(Exception_).filter(Exception_.case_id == case_id, Exception_.org_id == org_id_val).count()
            counts["cps"] = db.query(ConditionPrecedent).filter(ConditionPrecedent.case_id == case_id, ConditionPrecedent.org_id == org_id_val).count()
            counts["rule_runs"] = db.query(RuleRun).filter(RuleRun.case_id == case_id, RuleRun.org_id == org_id_val).count()
            counts["dossier_fields"] = db.query(CaseDossierField).filter(CaseDossierField.case_id == case_id, CaseDossierField.org_id == org_id_val).count()
            deleted_case_ids.append(str(case_id))
            total_db_rows += 1 + counts["exports"] + counts["document_pages"] + counts["documents"] + counts["exceptions"] + counts["cps"] + counts["rule_runs"] + counts["dossier_fields"]
            continue

        # 1) Exports (DB + MinIO keys if any)
        exports = db.query(Export).filter(Export.case_id == case_id, Export.org_id == org_id_val).all()
        for exp in exports:
            if exp.minio_key:
                try:
                    client = get_s3_client()
                    client.delete_object(Bucket=settings.MINIO_BUCKET, Key=exp.minio_key)
                    total_minio_objects += 1
                except ClientError as e:
                    if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey", "NoSuchBucket"):
                        raise
            db.delete(exp)
            counts["exports"] += 1
        total_db_rows += len(exports)

        # 2) Document pages (and OCR-related)
        doc_ids = [r[0] for r in db.query(Document.id).filter(Document.case_id == case_id, Document.org_id == org_id_val).all()]
        if doc_ids:
            db.query(OCRTextCorrection).filter(OCRTextCorrection.document_id.in_(doc_ids)).delete(synchronize_session=False)
            db.query(OCRExtractionCandidate).filter(OCRExtractionCandidate.document_id.in_(doc_ids)).delete(synchronize_session=False)
            pages = db.query(DocumentPage).filter(DocumentPage.document_id.in_(doc_ids)).all()
            for p in pages:
                db.delete(p)
                counts["document_pages"] += 1
            total_db_rows += counts["document_pages"]

        # 3) Documents (DB) then MinIO per doc
        docs = db.query(Document).filter(Document.case_id == case_id, Document.org_id == org_id_val).all()
        for doc in docs:
            minio_prefix = f"org/{org_id_val}/cases/{case_id}/docs/{doc.id}/"
            total_minio_objects += _safe_delete_prefix(minio_prefix)
            db.delete(doc)
            counts["documents"] += 1
        total_db_rows += len(docs)

        # 4) Exception evidence refs, CP evidence refs, then exceptions, CPs, rule runs
        exc_ids = [e[0] for e in db.query(Exception_.id).filter(Exception_.case_id == case_id, Exception_.org_id == org_id_val).all()]
        if exc_ids:
            db.query(ExceptionEvidenceRef).filter(ExceptionEvidenceRef.exception_id.in_(exc_ids)).delete(synchronize_session=False)
        cp_ids = [c[0] for c in db.query(ConditionPrecedent.id).filter(ConditionPrecedent.case_id == case_id, ConditionPrecedent.org_id == org_id_val).all()]
        if cp_ids:
            db.query(CPEvidenceRef).filter(CPEvidenceRef.cp_id.in_(cp_ids)).delete(synchronize_session=False)
        rule_run_count = db.query(RuleRun).filter(RuleRun.case_id == case_id, RuleRun.org_id == org_id_val).count()
        db.query(Exception_).filter(Exception_.case_id == case_id, Exception_.org_id == org_id_val).delete(synchronize_session=False)
        db.query(ConditionPrecedent).filter(ConditionPrecedent.case_id == case_id, ConditionPrecedent.org_id == org_id_val).delete(synchronize_session=False)
        db.query(RuleRun).filter(RuleRun.case_id == case_id, RuleRun.org_id == org_id_val).delete(synchronize_session=False)
        counts["exceptions"] = len(exc_ids)
        counts["cps"] = len(cp_ids)
        counts["rule_runs"] = rule_run_count
        total_db_rows += len(exc_ids) + len(cp_ids) + rule_run_count

        # Verifications (evidence refs first), approvals, notifications
        ver_ids = [v[0] for v in db.query(Verification.id).filter(Verification.case_id == case_id, Verification.org_id == org_id_val).all()]
        if ver_ids:
            db.query(VerificationEvidenceRef).filter(VerificationEvidenceRef.verification_id.in_(ver_ids)).delete(synchronize_session=False)
        db.query(Verification).filter(Verification.case_id == case_id, Verification.org_id == org_id_val).delete(synchronize_session=False)
        db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case_id).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.case_id == case_id).delete(synchronize_session=False)
        db.query(DossierFieldHistory).filter(DossierFieldHistory.case_id == case_id, DossierFieldHistory.org_id == org_id_val).delete(synchronize_session=False)
        db.query(CaseDossierField).filter(CaseDossierField.case_id == case_id, CaseDossierField.org_id == org_id_val).delete(synchronize_session=False)

        # Case MinIO prefix (exports dir, etc.)
        case_prefix = f"org/{org_id_val}/cases/{case_id}/"
        total_minio_objects += _safe_delete_prefix(case_prefix)

        db.delete(case)
        total_db_rows += 1
        deleted_case_ids.append(str(case_id))

        if not actor:
            pass  # no user in org to attribute; still delete, but no audit entry
        else:
            write_audit_event(
                db=db,
                org_id=org_id_val,
                actor_user_id=actor,
            action="retention.case_deleted",
            entity_type="case",
            entity_id=case_id,
            event_metadata={
                "case_id": str(case_id),
                "deleted_counts": counts,
                "request_id": REQUEST_ID_RETENTION,
            },
                request_id=REQUEST_ID_RETENTION,
            )
        db.commit()

    return {
        "cases_deleted": len(deleted_case_ids),
        "case_ids": deleted_case_ids,
        "total_db_rows": total_db_rows,
        "total_minio_objects": total_minio_objects,
        "cutoff_date": cutoff.isoformat(),
        "retention_days": days,
        "dry_run": dry_run,
    }
