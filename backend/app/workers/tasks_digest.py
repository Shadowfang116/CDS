"""Celery tasks for digest generation."""
import uuid
from datetime import datetime, timedelta
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal


@celery_app.task(name="digests.generate_pdf")
def generate_digest_pdf(run_id: str, actor_user_id: str):
    """Generate a digest PDF for a specific run."""
    from app.services.digest_generator import generate_digest_for_run
    
    db = SessionLocal()
    try:
        result = generate_digest_for_run(
            db=db,
            run_id=uuid.UUID(run_id),
            actor_user_id=uuid.UUID(actor_user_id),
        )
        return {"status": "success" if result else "failed", "run_id": run_id}
    finally:
        db.close()


@celery_app.task(name="digests.run_due_schedules")
def run_due_schedules():
    """
    Check for due digest schedules and trigger runs.
    Called periodically by Celery beat (every 5 minutes).
    """
    from app.models.digest import DigestSchedule, DigestRun
    from app.services.audit import write_audit_event
    
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        current_hour = now.hour
        current_weekday = now.weekday()  # 0=Monday
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=current_weekday)
        
        # Get all enabled schedules
        schedules = db.query(DigestSchedule).filter(
            DigestSchedule.is_enabled == True
        ).all()
        
        triggered = 0
        
        for schedule in schedules:
            should_run = False
            
            if schedule.cadence == "daily":
                # Check if hour matches and no run today
                if schedule.hour_local == current_hour:
                    last_run = db.query(DigestRun).filter(
                        DigestRun.schedule_id == schedule.id,
                        DigestRun.run_at >= today_start,
                    ).first()
                    if not last_run:
                        should_run = True
            
            elif schedule.cadence == "weekly":
                # Check if weekday and hour match and no run this week
                if schedule.weekday == current_weekday and schedule.hour_local == current_hour:
                    last_run = db.query(DigestRun).filter(
                        DigestRun.schedule_id == schedule.id,
                        DigestRun.run_at >= week_start,
                    ).first()
                    if not last_run:
                        should_run = True
            
            if should_run:
                # Create run record
                run = DigestRun(
                    org_id=schedule.org_id,
                    schedule_id=schedule.id,
                    run_at=now,
                    status="pending",
                )
                db.add(run)
                db.commit()
                db.refresh(run)
                
                # Trigger async generation
                generate_digest_pdf.delay(str(run.id), str(schedule.created_by_user_id))
                triggered += 1
        
        return {"checked": len(schedules), "triggered": triggered}
    
    finally:
        db.close()

