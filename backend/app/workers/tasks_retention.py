"""Phase 9: Celery task for retention — delete Closed cases older than RETENTION_DAYS (scheduled daily)."""
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.org import Org


@celery_app.task(name="retention.run_retention_now")
def run_retention_now(dry_run: bool = False):
    """
    Run retention for all orgs: delete Closed cases older than RETENTION_DAYS.
    Emits retention.case_deleted audit event per case. Idempotent.
    Called by beat daily at 2am UTC; can be triggered manually.
    """
    from app.services.retention import run_retention_for_org

    db = SessionLocal()
    try:
        org_ids = [row[0] for row in db.query(Org.id).all()]
        total_cases = 0
        total_db_rows = 0
        total_minio = 0
        by_org = []
        for org_id in org_ids:
            result = run_retention_for_org(db=db, org_id=org_id, actor_user_id=None, dry_run=dry_run)
            total_cases += result["cases_deleted"]
            total_db_rows += result["total_db_rows"]
            total_minio += result["total_minio_objects"]
            by_org.append({"org_id": str(org_id), **result})
        return {
            "status": "ok",
            "dry_run": dry_run,
            "orgs_processed": len(org_ids),
            "cases_deleted": total_cases,
            "total_db_rows": total_db_rows,
            "total_minio_objects": total_minio,
            "by_org": by_org,
        }
    finally:
        db.close()
