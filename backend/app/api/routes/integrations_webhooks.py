"""Webhook endpoints management API (Admin only)."""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from app.db.session import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.audit import write_audit_event
from app.models.webhook import WebhookEndpoint, WebhookDelivery
from app.services.crypto import encrypt_string, generate_secret, get_secret_preview

router = APIRouter(prefix="/integrations/webhooks", tags=["integrations"])


class WebhookEndpointCreate(BaseModel):
    name: str
    url: str
    subscribed_events: List[str]


class WebhookEndpointUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    is_enabled: Optional[bool] = None
    subscribed_events: Optional[List[str]] = None


class WebhookEndpointResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    is_enabled: bool
    secret_preview: str
    subscribed_events: List[str]
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    endpoint_id: uuid.UUID
    event_type: str
    status: str
    attempt_count: int
    http_status: Optional[int]
    response_body_snippet: Optional[str]
    last_error: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]


@router.get("", response_model=List[WebhookEndpointResponse])
async def list_webhooks(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhook endpoints for the org (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage webhooks")
    
    endpoints = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.org_id == current_user.org_id
    ).order_by(WebhookEndpoint.created_at.desc()).all()
    
    return [
        WebhookEndpointResponse(
            id=ep.id,
            name=ep.name,
            url=ep.url,
            is_enabled=ep.is_enabled,
            secret_preview=ep.secret_preview,
            subscribed_events=ep.subscribed_events or [],
            created_at=ep.created_at,
            updated_at=ep.updated_at,
        )
        for ep in endpoints
    ]


@router.post("", response_model=dict, status_code=201)
async def create_webhook(
    request: Request,
    payload: WebhookEndpointCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a webhook endpoint (Admin only). Returns secret ONCE."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can create webhooks")
    
    # Validate URL
    try:
        HttpUrl(payload.url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # Validate events
    valid_events = ["approval.pending", "approval.decided", "case.decided", "export.generated"]
    for event in payload.subscribed_events:
        if event not in valid_events:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event}")
    
    # Generate and encrypt secret
    try:
        secret = generate_secret()
        secret_ciphertext = encrypt_string(secret)
        secret_preview = get_secret_preview(secret)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Cannot encrypt secret: {str(e)}")
    
    # Create endpoint
    endpoint = WebhookEndpoint(
        org_id=current_user.org_id,
        name=payload.name,
        url=payload.url,
        is_enabled=True,
        secret_ciphertext=secret_ciphertext,
        secret_preview=secret_preview,
        subscribed_events=payload.subscribed_events,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.webhook.create",
        entity_type="webhook_endpoint",
        entity_id=endpoint.id,
        event_metadata={
            "name": endpoint.name,
            "url": endpoint.url,
            "events": payload.subscribed_events,
        },
    )
    
    # Return secret ONCE (never again)
    return {
        "id": str(endpoint.id),
        "name": endpoint.name,
        "url": endpoint.url,
        "secret": secret,  # Only returned on creation
        "warning": "Save this secret now. It will not be shown again.",
    }


@router.patch("/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook(
    request: Request,
    endpoint_id: uuid.UUID,
    payload: WebhookEndpointUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a webhook endpoint (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can update webhooks")
    
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    # Update fields
    if payload.name is not None:
        endpoint.name = payload.name
    if payload.url is not None:
        try:
            HttpUrl(payload.url)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        endpoint.url = payload.url
    if payload.is_enabled is not None:
        endpoint.is_enabled = payload.is_enabled
    if payload.subscribed_events is not None:
        valid_events = ["approval.pending", "approval.decided", "case.decided", "export.generated"]
        for event in payload.subscribed_events:
            if event not in valid_events:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event}")
        endpoint.subscribed_events = payload.subscribed_events
    
    endpoint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(endpoint)
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.webhook.update",
        entity_type="webhook_endpoint",
        entity_id=endpoint.id,
        event_metadata={
            "name": endpoint.name,
            "is_enabled": endpoint.is_enabled,
        },
    )
    
    return WebhookEndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        url=endpoint.url,
        is_enabled=endpoint.is_enabled,
        secret_preview=endpoint.secret_preview,
        subscribed_events=endpoint.subscribed_events or [],
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


@router.delete("/{endpoint_id}", status_code=204)
async def delete_webhook(
    request: Request,
    endpoint_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a webhook endpoint (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete webhooks")
    
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    # Audit log before deletion
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.webhook.delete",
        entity_type="webhook_endpoint",
        entity_id=endpoint.id,
        event_metadata={"name": endpoint.name},
    )
    
    db.delete(endpoint)
    db.commit()


@router.get("/{endpoint_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_deliveries(
    request: Request,
    endpoint_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List webhook deliveries for an endpoint (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can view deliveries")
    
    # Verify endpoint belongs to org
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.endpoint_id == endpoint_id,
        WebhookDelivery.org_id == current_user.org_id,
    ).order_by(WebhookDelivery.created_at.desc()).limit(limit).all()
    
    return [
        WebhookDeliveryResponse(
            id=d.id,
            endpoint_id=d.endpoint_id,
            event_type=d.event_type,
            status=d.status,
            attempt_count=d.attempt_count,
            http_status=d.http_status,
            response_body_snippet=d.response_body_snippet,
            last_error=d.last_error,
            created_at=d.created_at,
            delivered_at=d.delivered_at,
        )
        for d in deliveries
    ]


@router.post("/{endpoint_id}/test", status_code=200)
async def test_webhook(
    request: Request,
    endpoint_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a test webhook event (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can test webhooks")
    
    endpoint = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    # Emit test event
    from app.services.event_bus import emit_event
    
    test_event = emit_event(
        db=db,
        org_id=current_user.org_id,
        event_type="export.generated",  # Use a safe test event
        payload={
            "test": True,
            "endpoint_id": str(endpoint_id),
            "triggered_by": current_user.user_id.hex,
        },
    )
    
    # Audit log
    write_audit_event(
        db=db,
        org_id=current_user.org_id,
        actor_user_id=current_user.user_id,
        action="integrations.webhook.test",
        entity_type="webhook_endpoint",
        entity_id=endpoint.id,
        event_metadata={"event_id": str(test_event.id)},
    )
    
    return {"message": "Test event emitted", "event_id": str(test_event.id)}

