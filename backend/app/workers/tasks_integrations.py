"""Celery tasks for processing integration events (email/webhooks)."""
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import SessionLocal
from app.models.integration_event import IntegrationEvent
from app.services.webhooks_sender import deliver_event_to_endpoints
from app.services.email_sender import deliver_event_via_email
from app.services.audit import write_audit_event
from app.workers.celery_app import celery_app


def _calculate_backoff(attempts: int) -> timedelta:
    """Calculate exponential backoff delay."""
    # 1m, 5m, 15m, 1h, 1h (cap at 1 hour)
    delays = [60, 300, 900, 3600, 3600]  # seconds
    idx = min(attempts - 1, len(delays) - 1)
    return timedelta(seconds=delays[idx])


@celery_app.task(name="integrations.process_integration_events")
def process_integration_events():
    """
    Process pending integration events from outbox.
    Claims events using FOR UPDATE SKIP LOCKED pattern.
    """
    db: Session = SessionLocal()
    worker_id = f"worker-{os.getpid()}"
    max_events_per_run = 50
    max_attempts = 5
    
    try:
        # Claim pending events due for processing (FOR UPDATE SKIP LOCKED)
        now = datetime.utcnow()
        # Events that are Pending and either have no next_attempt_at or it's in the past
        events = db.query(IntegrationEvent).filter(
            and_(
                IntegrationEvent.status == "Pending",
                (IntegrationEvent.next_attempt_at.is_(None) | (IntegrationEvent.next_attempt_at <= now)),
            )
        ).with_for_update(skip_locked=True).limit(max_events_per_run).all()
        
        if not events:
            return {"processed": 0, "success": 0, "failed": 0}
        
        processed = 0
        success = 0
        failed = 0
        
        for event in events:
            # Lock the event
            event.status = "Processing"
            event.locked_at = now
            event.locked_by = worker_id
            db.commit()
            
            try:
                # Attempt webhook delivery
                webhook_deliveries = deliver_event_to_endpoints(db, event)
                
                # Attempt email delivery
                email_deliveries = deliver_event_via_email(db, event)
                
                # Mark event as Done
                event.status = "Done"
                event.attempts += 1
                event.next_attempt_at = None
                event.locked_at = None
                event.locked_by = None
                
                # Audit log
                write_audit_event(
                    db=db,
                    org_id=event.org_id,
                    actor_user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # System
                    action="integrations.event.processed",
                    entity_type="integration_event",
                    entity_id=event.id,
                    event_metadata={
                        "event_type": event.event_type,
                        "webhook_deliveries": len(webhook_deliveries),
                        "email_deliveries": len(email_deliveries),
                    },
                )
                
                db.commit()
                success += 1
            
            except Exception as e:
                # Increment attempts and schedule retry
                event.attempts += 1
                event.last_error = str(e)[:500]
                
                if event.attempts >= max_attempts:
                    event.status = "Failed"
                    event.next_attempt_at = None
                    failed += 1
                    
                    # Audit log failure
                    write_audit_event(
                        db=db,
                        org_id=event.org_id,
                        actor_user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                        action="integrations.event.failed",
                        entity_type="integration_event",
                        entity_id=event.id,
                        event_metadata={
                            "event_type": event.event_type,
                            "attempts": event.attempts,
                            "error": event.last_error,
                        },
                    )
                else:
                    # Schedule retry
                    event.status = "Pending"
                    event.next_attempt_at = now + _calculate_backoff(event.attempts)
                
                event.locked_at = None
                event.locked_by = None
                db.commit()
                failed += 1
            
            processed += 1
        
        return {
            "processed": processed,
            "success": success,
            "failed": failed,
        }
    
    finally:
        db.close()

