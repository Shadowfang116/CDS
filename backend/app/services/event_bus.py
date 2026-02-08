"""Event bus for emitting integration events (email/webhooks)."""
import uuid
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.integration_event import IntegrationEvent


def emit_event(
    db: Session,
    org_id: uuid.UUID,
    event_type: str,
    payload: Dict[str, Any],
) -> IntegrationEvent:
    """
    Emit an integration event (creates outbox record).
    
    Event types:
    - approval.pending: when approval request created
    - approval.decided: when approval request approved/rejected
    - case.decided: when case decision recorded (PASS/CONDITIONAL_PASS/FAIL)
    - export.generated: when export is generated
    """
    event = IntegrationEvent(
        org_id=org_id,
        event_type=event_type,
        payload_json=payload,
        status="Pending",
        attempts=0,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

