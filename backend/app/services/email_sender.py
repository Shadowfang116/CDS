"""Email sending service with template rendering."""
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.integration_event import IntegrationEvent
from app.models.email_template import EmailTemplate, EmailDelivery
from app.models.user import User, UserOrgRole


def render_template(template_key: str, payload: Dict[str, Any]) -> tuple[str, str]:
    """
    Render email template with simple {{var}} replacement.
    Returns (subject, body_html).
    """
    # Default templates if not found in DB
    default_templates = {
        "approval.pending": {
            "subject": "Approval Required: {{request_type}}",
            "body": "A new approval request for {{request_type}} is pending for case: {{case_title}}.\n\nRequested by: {{requested_by_email}}\nCase ID: {{case_id}}",
        },
        "approval.decided": {
            "subject": "Approval Decision: {{request_type}}",
            "body": "Your approval request for {{request_type}} has been {{decision}}.\n\nCase: {{case_title}}\nReason: {{reason}}",
        },
        "case.decided": {
            "subject": "Case Decision: {{case_title}}",
            "body": "Case {{case_title}} has been decided: {{decision}}.\n\nRationale: {{rationale}}\nCase ID: {{case_id}}",
        },
        "export.generated": {
            "subject": "Export Generated: {{export_type}}",
            "body": "Export {{export_type}} has been generated for case: {{case_title}}.\n\nFilename: {{filename}}\nCase ID: {{case_id}}",
        },
    }
    
    template = default_templates.get(template_key, {
        "subject": "Notification: {{event_type}}",
        "body": "Event {{event_type}} occurred.\n\n{{payload}}",
    })
    
    subject = template["subject"]
    body = template["body"]
    
    # Simple {{var}} replacement
    def replace_var(match):
        var_name = match.group(1)
        # Support nested access like case.title
        parts = var_name.split(".")
        value = payload
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                value = ""
                break
        return str(value) if value is not None else ""
    
    subject = re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, subject)
    body = re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, body)
    
    # Convert markdown-like to HTML (very basic)
    body_html = body.replace("\n", "<br>\n")
    
    return subject, body_html


def send_email(
    db: Session,
    to_email: str,
    subject: str,
    body_html: str,
) -> bool:
    """
    Send email via SMTP.
    Returns True if successful, False otherwise.
    """
    if not settings.EMAIL_ENABLED:
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        part = MIMEText(body_html, "html")
        msg.attach(part)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        # Log error but don't raise
        print(f"Email send failed: {str(e)}")
        return False


def get_email_recipients(
    db: Session,
    org_id: uuid.UUID,
    event_type: str,
    payload: Dict[str, Any],
) -> List[str]:
    """
    Get list of email addresses to notify based on event type and payload.
    
    Recipient mapping:
    - approval.pending: all users with role Admin or Approver
    - approval.decided: requested_by_email from payload
    - case.decided: all users with role Admin
    - export.generated: (optional, can be empty or admin)
    """
    recipients = []
    
    if event_type == "approval.pending":
        # Notify Admin and Approver roles
        user_roles = db.query(UserOrgRole).filter(
            UserOrgRole.org_id == org_id,
            UserOrgRole.role.in_(["Admin", "Approver"]),
        ).all()
        user_ids = [ur.user_id for ur in user_roles]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        recipients = [u.email for u in users if u.email]
    
    elif event_type == "approval.decided":
        # Notify requester
        requested_by_email = payload.get("requested_by_email")
        if requested_by_email:
            recipients = [requested_by_email]
    
    elif event_type == "case.decided":
        # Notify Admin role
        user_roles = db.query(UserOrgRole).filter(
            UserOrgRole.org_id == org_id,
            UserOrgRole.role == "Admin",
        ).all()
        user_ids = [ur.user_id for ur in user_roles]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        recipients = [u.email for u in users if u.email]
    
    elif event_type == "export.generated":
        # Optional: notify Admin or leave empty
        user_roles = db.query(UserOrgRole).filter(
            UserOrgRole.org_id == org_id,
            UserOrgRole.role == "Admin",
        ).all()
        user_ids = [ur.user_id for ur in user_roles]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        recipients = [u.email for u in users if u.email]
    
    return recipients


def deliver_event_via_email(
    db: Session,
    event: IntegrationEvent,
) -> List[EmailDelivery]:
    """
    Deliver an integration event via email to appropriate recipients.
    Returns list of EmailDelivery records.
    """
    if not settings.EMAIL_ENABLED:
        return []
    
    # Get template for this event type (or use default)
    template = db.query(EmailTemplate).filter(
        EmailTemplate.org_id == event.org_id,
        EmailTemplate.template_key == event.event_type,
        EmailTemplate.is_enabled == True,
    ).first()
    
    # Get recipients
    recipients = get_email_recipients(db, event.org_id, event.event_type, event.payload_json)
    
    if not recipients:
        # No recipients, mark as Done (no-op)
        return []
    
    deliveries = []
    
    for to_email in recipients:
        # Render template
        if template:
            subject = template.subject
            body_html = template.body_md.replace("\n", "<br>\n")
            # Apply template variables (simple {{var}} replacement)
            def replace_vars(text: str, data: Dict[str, Any]) -> str:
                for key, value in data.items():
                    text = text.replace(f"{{{{{key}}}}}", str(value))
                    # Also support nested keys like case.title
                    if isinstance(value, dict):
                        for nested_key, nested_value in value.items():
                            text = text.replace(f"{{{{{key}.{nested_key}}}}}", str(nested_value))
                return text
            subject = replace_vars(subject, event.payload_json)
            body_html = replace_vars(body_html, event.payload_json)
        else:
            subject, body_html = render_template(event.event_type, event.payload_json)
        
        # Create delivery record
        delivery = EmailDelivery(
            org_id=event.org_id,
            to_email=to_email,
            template_key=event.event_type,
            subject=subject,
            status="Pending",
            attempt_count=0,
            created_at=datetime.utcnow(),
        )
        db.add(delivery)
        db.flush()
        
        # Send email
        success = send_email(db, to_email, subject, body_html)
        
        if success:
            delivery.status = "Success"
            delivery.sent_at = datetime.utcnow()
        else:
            delivery.status = "Failed"
            delivery.last_error = "SMTP send failed"
        
        delivery.attempt_count = 1
        db.commit()
        deliveries.append(delivery)
    
    return deliveries

