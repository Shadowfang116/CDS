"""Phase 8: Celery tasks for async export generation (bank pack)."""
import time
import uuid
from datetime import datetime

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.export import Export, EXPORT_STATUS_PENDING, EXPORT_STATUS_RUNNING, EXPORT_STATUS_SUCCEEDED, EXPORT_STATUS_FAILED, ERROR_MESSAGE_MAX_LENGTH
from app.services.audit import write_audit_event
from app.services.storage import put_object_bytes

GENERATION_ERROR = "GENERATION_ERROR"


def _truncate_message(msg: str, max_len: int = ERROR_MESSAGE_MAX_LENGTH) -> str:
    if not msg or len(msg) <= max_len:
        return msg or ""
    return msg[: max_len - 3] + "..."


@celery_app.task(name="exports.generate_bank_pack", bind=True)
def generate_bank_pack_task(self, org_id: str, case_id: str, export_id: str, request_id: str = None):
    """
    Generate Bank Pack PDF for a case. Tenant-scoped; marks export running then succeeded/failed.
    Always sets finished_at. Uses request_id for audit correlation.
    """
    org_uuid = uuid.UUID(org_id)
    case_uuid = uuid.UUID(case_id)
    export_uuid = uuid.UUID(export_id)
    start_ms = time.time()
    db = SessionLocal()
    try:
        export = db.query(Export).filter(
            Export.id == export_uuid,
            Export.org_id == org_uuid,
            Export.case_id == case_uuid,
        ).first()
        if not export:
            return {"status": "error", "message": "Export not found"}
        if export.status != EXPORT_STATUS_PENDING:
            return {"status": "skipped", "export_status": export.status}

        export.status = EXPORT_STATUS_RUNNING
        export.started_at = datetime.utcnow()
        if request_id:
            export.request_id = request_id
        db.commit()

        from app.api.routes.exports import _load_case_data
        from app.services.export_bank_pack import generate_bank_pack_pdf

        data = _load_case_data(db, case_uuid, org_uuid)
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

        minio_key = f"org/{org_uuid}/cases/{case_uuid}/exports/{export_uuid}/{filename}"
        put_object_bytes(minio_key, pdf_bytes, "application/pdf")

        export.status = EXPORT_STATUS_SUCCEEDED
        export.finished_at = datetime.utcnow()
        export.minio_key = minio_key
        export.filename = filename
        export.content_type = "application/pdf"
        export.error_code = None
        export.error_message = None
        db.commit()
        db.refresh(export)

        duration_ms = int((time.time() - start_ms) * 1000)
        write_audit_event(
            db=db,
            org_id=org_uuid,
            actor_user_id=export.created_by_user_id,
            action="export.succeeded",
            entity_type="export",
            entity_id=export.id,
            event_metadata={
                "export_id": str(export.id),
                "case_id": str(case_uuid),
                "request_id": request_id,
                "storage_key": minio_key,
                "duration_ms": duration_ms,
            },
            request_id=request_id,
        )
        return {"status": "succeeded", "export_id": export_id, "duration_ms": duration_ms}

    except Exception as e:
        duration_ms = int((time.time() - start_ms) * 1000)
        error_code = getattr(e, "error_code", None) or GENERATION_ERROR
        error_message = _truncate_message(str(e))

        export = db.query(Export).filter(
            Export.id == export_uuid,
            Export.org_id == org_uuid,
        ).first()
        if export:
            export.status = EXPORT_STATUS_FAILED
            export.finished_at = datetime.utcnow()
            export.error_code = error_code
            export.error_message = error_message
            db.commit()
            write_audit_event(
                db=db,
                org_id=org_uuid,
                actor_user_id=export.created_by_user_id,
                action="export.failed",
                entity_type="export",
                entity_id=export.id,
                event_metadata={
                    "export_id": str(export.id),
                    "case_id": str(case_uuid),
                    "request_id": request_id,
                    "error_code": error_code,
                    "error_message": error_message,
                    "duration_ms": duration_ms,
                },
                request_id=request_id,
            )
        return {"status": "failed", "export_id": export_id, "error_code": error_code, "duration_ms": duration_ms}
    finally:
        try:
            export = db.query(Export).filter(Export.id == export_uuid, Export.org_id == org_uuid).first()
            if export and export.finished_at is None:
                export.finished_at = datetime.utcnow()
                if export.status == EXPORT_STATUS_RUNNING:
                    export.status = EXPORT_STATUS_FAILED
                    export.error_code = export.error_code or GENERATION_ERROR
                    export.error_message = export.error_message or "Task finished without setting result"
                db.commit()
        except Exception:
            pass
        finally:
            db.close()
