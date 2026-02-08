"""Webhook delivery service with HMAC signing."""
import hmac
import hashlib
import base64
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.models.integration_event import IntegrationEvent
from app.models.webhook import WebhookEndpoint, WebhookDelivery
from app.services.crypto import decrypt_string


def _sign_payload(secret: str, payload: bytes, timestamp: str, delivery_id: str) -> str:
    """Generate HMAC SHA256 signature for webhook payload."""
    message = f"{timestamp}.{delivery_id}.{payload.decode()}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()


def deliver_event_to_endpoints(
    db: Session,
    event: IntegrationEvent,
) -> List[WebhookDelivery]:
    """
    Deliver an integration event to all enabled webhook endpoints subscribed to the event type.
    Returns list of WebhookDelivery records.
    """
    if not settings.WEBHOOK_DELIVERY_ENABLED:
        return []
    
    # Find enabled endpoints for this org subscribed to this event type
    endpoints = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.org_id == event.org_id,
        WebhookEndpoint.is_enabled == True,
    ).all()
    
    subscribed_endpoints = [
        ep for ep in endpoints
        if event.event_type in (ep.subscribed_events or [])
    ]
    
    deliveries = []
    
    for endpoint in subscribed_endpoints:
        delivery = WebhookDelivery(
            org_id=event.org_id,
            endpoint_id=endpoint.id,
            event_type=event.event_type,
            payload_json=event.payload_json,
            status="Pending",
            attempt_count=0,
            created_at=datetime.utcnow(),
        )
        db.add(delivery)
        db.flush()  # Get delivery.id
        
        # Decrypt secret
        try:
            secret = decrypt_string(endpoint.secret_ciphertext)
        except Exception as e:
            delivery.status = "Failed"
            delivery.last_error = f"Secret decryption failed: {str(e)}"
            db.commit()
            deliveries.append(delivery)
            continue
        
        # Prepare payload
        import json
        payload_dict = {
            "event": event.event_type,
            "org_id": str(event.org_id),
            "data": event.payload_json,
            "timestamp": datetime.utcnow().isoformat(),
        }
        payload_json_str = json.dumps(payload_dict, sort_keys=True)
        payload_bytes = payload_json_str.encode()
        
        # Generate signature headers
        timestamp = str(int(datetime.utcnow().timestamp()))
        delivery_id = str(delivery.id)
        signature = _sign_payload(secret, payload_bytes, timestamp, delivery_id)
        
        # Send webhook
        try:
            with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
                response = client.post(
                    endpoint.url,
                    json=payload_dict,
                    headers={
                        "X-BDP-Event": event.event_type,
                        "X-BDP-Org": str(event.org_id),
                        "X-BDP-Signature": signature,
                        "X-BDP-Timestamp": timestamp,
                        "X-BDP-Delivery-Id": delivery_id,
                        "Content-Type": "application/json",
                    },
                )
                
                delivery.status = "Success" if 200 <= response.status_code < 300 else "Failed"
                delivery.http_status = response.status_code
                delivery.attempt_count = 1
                delivery.delivered_at = datetime.utcnow()
                
                # Store response snippet (first 500 chars)
                try:
                    response_text = response.text[:500]
                    delivery.response_body_snippet = response_text
                except Exception:
                    pass
                
                if delivery.status == "Failed":
                    delivery.last_error = f"HTTP {response.status_code}: {response_text[:200] if 'response_text' in locals() else 'Unknown error'}"
        
        except httpx.TimeoutException:
            delivery.status = "Failed"
            delivery.last_error = f"Request timeout after {settings.WEBHOOK_TIMEOUT_SECONDS}s"
            delivery.attempt_count = 1
        
        except Exception as e:
            delivery.status = "Failed"
            delivery.last_error = f"Delivery failed: {str(e)}"
            delivery.attempt_count = 1
        
        db.commit()
        deliveries.append(delivery)
    
    return deliveries

