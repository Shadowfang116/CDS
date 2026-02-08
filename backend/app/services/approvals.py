"""Approval workflow service for maker/checker controls."""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.approval import ApprovalRequest, APPROVAL_REQUEST_TYPES, CASE_DECISIONS
from app.models.case import Case
from app.models.rules import Exception_, ConditionPrecedent
from app.models.export import Export
from app.services.audit import write_audit_event
from app.services.notifications import notify_user, notify_approvers


def validate_request_payload(request_type: str, payload: Dict[str, Any]) -> None:
    """Validate payload structure for each request type."""
    if request_type == "exception_waive":
        if "exception_id" not in payload:
            raise HTTPException(status_code=400, detail="exception_id required for exception_waive")
        if "waiver_reason" not in payload:
            raise HTTPException(status_code=400, detail="waiver_reason required for exception_waive")
    
    elif request_type == "cp_waive":
        if "cp_id" not in payload:
            raise HTTPException(status_code=400, detail="cp_id required for cp_waive")
        if "waiver_reason" not in payload:
            raise HTTPException(status_code=400, detail="waiver_reason required for cp_waive")
    
    elif request_type == "case_decision":
        if "decision" not in payload:
            raise HTTPException(status_code=400, detail="decision required for case_decision")
        if payload["decision"] not in CASE_DECISIONS:
            raise HTTPException(status_code=400, detail=f"decision must be one of: {CASE_DECISIONS}")
        if "rationale" not in payload:
            raise HTTPException(status_code=400, detail="rationale required for case_decision")
    
    elif request_type == "export_release":
        if "export_id" not in payload:
            raise HTTPException(status_code=400, detail="export_id required for export_release")


def create_approval_request(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
    requested_by_role: str,
    request_type: str,
    payload: Dict[str, Any],
) -> ApprovalRequest:
    """
    Create an approval request (maker action).
    Validates permissions, entity existence, and prevents duplicates.
    """
    # Validate request type
    if request_type not in APPROVAL_REQUEST_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid request_type: {request_type}")
    
    # Validate role (Reviewer or Admin can create requests)
    if requested_by_role not in ["Reviewer", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Reviewer or Admin can create approval requests")
    
    # Validate payload
    validate_request_payload(request_type, payload)
    
    # Verify case exists and belongs to org
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate referenced entities exist and belong to org
    if request_type == "exception_waive":
        exception = db.query(Exception_).filter(
            Exception_.id == uuid.UUID(payload["exception_id"]),
            Exception_.org_id == org_id,
        ).first()
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        if exception.status == "Waived":
            raise HTTPException(status_code=400, detail="Exception already waived")
    
    elif request_type == "cp_waive":
        cp = db.query(ConditionPrecedent).filter(
            ConditionPrecedent.id == uuid.UUID(payload["cp_id"]),
            ConditionPrecedent.org_id == org_id,
        ).first()
        if not cp:
            raise HTTPException(status_code=404, detail="Condition Precedent not found")
        if cp.status == "Waived":
            raise HTTPException(status_code=400, detail="CP already waived")
    
    elif request_type == "export_release":
        export = db.query(Export).filter(
            Export.id == uuid.UUID(payload["export_id"]),
            Export.org_id == org_id,
        ).first()
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")
    
    # Check for duplicate pending request
    existing = db.query(ApprovalRequest).filter(
        ApprovalRequest.org_id == org_id,
        ApprovalRequest.request_type == request_type,
        ApprovalRequest.status == "Pending",
    )
    
    if request_type == "exception_waive":
        existing = existing.filter(
            ApprovalRequest.payload_json["exception_id"].astext == payload["exception_id"]
        )
    elif request_type == "cp_waive":
        existing = existing.filter(
            ApprovalRequest.payload_json["cp_id"].astext == payload["cp_id"]
        )
    elif request_type == "case_decision":
        existing = existing.filter(ApprovalRequest.case_id == case_id)
    elif request_type == "export_release":
        existing = existing.filter(
            ApprovalRequest.payload_json["export_id"].astext == payload["export_id"]
        )
    
    if existing.first():
        raise HTTPException(status_code=400, detail="A pending request already exists for this item")
    
    # Create the request
    approval_request = ApprovalRequest(
        org_id=org_id,
        case_id=case_id,
        requested_by_user_id=requested_by_user_id,
        requested_by_role=requested_by_role,
        request_type=request_type,
        status="Pending",
        payload_json=payload,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(approval_request)
    db.commit()
    db.refresh(approval_request)
    
    # Notify approvers
    type_label = APPROVAL_REQUEST_TYPES.get(request_type, request_type)
    notify_approvers(
        db=db,
        org_id=org_id,
        title=f"Approval Required: {type_label}",
        body=f"A new {type_label.lower()} request is pending approval for case: {case.title}",
        severity="warning",
        entity_type="approval",
        entity_id=approval_request.id,
        case_id=case_id,
        exclude_user_id=requested_by_user_id,
    )
    
    return approval_request


def decide_approval_request(
    db: Session,
    request_id: uuid.UUID,
    decided_by_user_id: uuid.UUID,
    decided_by_role: str,
    org_id: uuid.UUID,
    approve: bool,
    reason: Optional[str] = None,
) -> ApprovalRequest:
    """
    Approve or reject an approval request (checker action).
    Enforces dual control: requester cannot be decider.
    """
    # Validate role
    if decided_by_role not in ["Approver", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Approver or Admin can decide approval requests")
    
    # Get the request
    approval_request = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == request_id,
        ApprovalRequest.org_id == org_id,
    ).first()
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Request is already {approval_request.status}")
    
    # Enforce dual control
    if approval_request.requested_by_user_id == decided_by_user_id:
        raise HTTPException(
            status_code=403,
            detail="Dual control violation: You cannot approve your own request"
        )
    
    # Update the request
    approval_request.decided_by_user_id = decided_by_user_id
    approval_request.decided_at = datetime.utcnow()
    approval_request.decision_reason = reason
    approval_request.status = "Approved" if approve else "Rejected"
    approval_request.updated_at = datetime.utcnow()
    
    # Apply side effects if approved
    if approve:
        apply_approval_side_effects(db, approval_request, decided_by_user_id)
    
    db.commit()
    db.refresh(approval_request)
    
    # Notify the requester
    status_text = "approved" if approve else "rejected"
    type_label = APPROVAL_REQUEST_TYPES.get(approval_request.request_type, approval_request.request_type)
    notify_user(
        db=db,
        org_id=org_id,
        user_id=approval_request.requested_by_user_id,
        notification_type="approval_decided",
        title=f"Request {status_text.title()}: {type_label}",
        body=f"Your {type_label.lower()} request has been {status_text}." + (f" Reason: {reason}" if reason else ""),
        severity="info" if approve else "warning",
        entity_type="approval",
        entity_id=approval_request.id,
        case_id=approval_request.case_id,
    )
    
    return approval_request


def apply_approval_side_effects(
    db: Session,
    approval_request: ApprovalRequest,
    decided_by_user_id: uuid.UUID,
) -> None:
    """Apply side effects when an approval request is approved."""
    payload = approval_request.payload_json
    now = datetime.utcnow()
    
    if approval_request.request_type == "exception_waive":
        exception = db.query(Exception_).filter(
            Exception_.id == uuid.UUID(payload["exception_id"])
        ).first()
        if exception:
            exception.status = "Waived"
            exception.waiver_reason = payload.get("waiver_reason")
            exception.waived_at = now
            exception.waived_by_user_id = decided_by_user_id
            
            write_audit_event(
                db=db,
                org_id=approval_request.org_id,
                actor_user_id=decided_by_user_id,
                action="exception.waive",
                entity_type="exception",
                entity_id=exception.id,
                event_metadata={
                    "approval_request_id": str(approval_request.id),
                    "waiver_reason": payload.get("waiver_reason"),
                },
            )
    
    elif approval_request.request_type == "cp_waive":
        cp = db.query(ConditionPrecedent).filter(
            ConditionPrecedent.id == uuid.UUID(payload["cp_id"])
        ).first()
        if cp:
            cp.status = "Waived"
            cp.waiver_reason = payload.get("waiver_reason")
            cp.waived_at = now
            
            write_audit_event(
                db=db,
                org_id=approval_request.org_id,
                actor_user_id=decided_by_user_id,
                action="cp.waive",
                entity_type="cp",
                entity_id=cp.id,
                event_metadata={
                    "approval_request_id": str(approval_request.id),
                    "waiver_reason": payload.get("waiver_reason"),
                },
            )
    
    elif approval_request.request_type == "case_decision":
        case = db.query(Case).filter(Case.id == approval_request.case_id).first()
        if case:
            case.decision = payload["decision"]
            case.decided_at = now
            case.decided_by_user_id = decided_by_user_id
            case.decision_notes = {
                "rationale": payload.get("rationale"),
                "conditions": payload.get("conditions", []),
                "effective_date": payload.get("effective_date"),
            }
            
            # Update case status based on decision
            if payload["decision"] == "PASS":
                case.status = "Approved"
            elif payload["decision"] == "FAIL":
                case.status = "Rejected"
            elif payload["decision"] == "CONDITIONAL_PASS":
                case.status = "Approved"  # With conditions
            
            write_audit_event(
                db=db,
                org_id=approval_request.org_id,
                actor_user_id=decided_by_user_id,
                action="case.decision",
                entity_type="case",
                entity_id=case.id,
                event_metadata={
                    "approval_request_id": str(approval_request.id),
                    "decision": payload["decision"],
                    "rationale": payload.get("rationale"),
                },
            )
            
            # Emit integration event
            from app.services.event_bus import emit_event
            emit_event(
                db=db,
                org_id=approval_request.org_id,
                event_type="case.decided",
                payload={
                    "case_id": str(case.id),
                    "case_title": case.title,
                    "decision": payload["decision"],
                    "rationale": payload.get("rationale"),
                    "decided_by_user_id": str(decided_by_user_id),
                },
            )


def cancel_approval_request(
    db: Session,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ApprovalRequest:
    """Cancel a pending approval request. Only the requester can cancel."""
    approval_request = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == request_id,
        ApprovalRequest.org_id == org_id,
    ).first()
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {approval_request.status} request")
    
    if approval_request.requested_by_user_id != user_id:
        raise HTTPException(status_code=403, detail="Only the requester can cancel their request")
    
    approval_request.status = "Cancelled"
    approval_request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(approval_request)
    
    return approval_request


def compute_case_risk_score(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Compute explainable risk score for a case (P9).
    
    Returns:
        {
            "score": int (0-100+),
            "label": "Green" | "Amber" | "Red",
            "high_count": int,
            "medium_count": int,
            "low_count": int,
            "hard_stop_count": int,
        }
    """
    from sqlalchemy import func
    
    # Count exceptions by severity
    high_exceptions = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status.in_(["Open", "Pending"]),
        Exception_.severity == "High",
    ).scalar() or 0
    
    medium_exceptions = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status.in_(["Open", "Pending"]),
        Exception_.severity == "Medium",
    ).scalar() or 0
    
    low_exceptions = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status.in_(["Open", "Pending"]),
        Exception_.severity == "Low",
    ).scalar() or 0
    
    # Count hard-stop exceptions (check if rule has is_hard_stop flag)
    # For now, we'll check if exception title contains "Hard-stop" or check rule metadata
    # In future, we can add is_hard_stop column to Exception_ model
    hard_stop_exceptions = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status.in_(["Open", "Pending"]),
        Exception_.severity == "High",
    ).all()
    
    # Check rule metadata for is_hard_stop (if stored in exception metadata)
    hard_stop_count = 0
    for exc in hard_stop_exceptions:
        # Check if rule_id indicates hard-stop (e.g., LDA_001, REG_001, TPA_CHAIN_GAP_001)
        if exc.rule_id and any(hs in exc.rule_id for hs in ["LDA_001", "REG_001", "TPA_CHAIN_GAP_001", "TPA_NOTICE_POSSESSION_001", "TPA_CAPACITY_001", "SOC_001", "SOC_002", "RUDA_001", "CANT_001"]):
            hard_stop_count += 1
    
    # Calculate risk score
    score = (high_exceptions * 10) + (medium_exceptions * 3) + (low_exceptions * 1) + (hard_stop_count * 25)
    
    # Map to label
    if score == 0:
        label = "Green"
    elif score < 25:
        label = "Amber"
    else:
        label = "Red"
    
    return {
        "score": score,
        "label": label,
        "high_count": high_exceptions,
        "medium_count": medium_exceptions,
        "low_count": low_exceptions,
        "hard_stop_count": hard_stop_count,
    }


def get_case_readiness(
    db: Session,
    case_id: uuid.UUID,
    org_id: uuid.UUID,
    cp_threshold_pct: float = 80.0,
) -> Dict[str, Any]:
    """
    Check if a case is ready for final approval.
    Returns readiness status and reasons.
    """
    from sqlalchemy import func, or_
    from app.models.verification import Verification
    
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        return {"ready": False, "reasons": ["Case not found"]}
    
    reasons = []
    
    # Check status
    if case.status not in ["Review", "Ready for Approval"]:
        reasons.append(f"Case status is '{case.status}', expected 'Review' or 'Ready for Approval'")
    
    # Check open high exceptions
    open_high = db.query(func.count(Exception_.id)).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.severity == "High",
        Exception_.status == "Open",
    ).scalar() or 0
    
    if open_high > 0:
        reasons.append(f"{open_high} open high-severity exception(s) remaining")
    
    # Check hard-stop exceptions (P9)
    hard_stop_exceptions = db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status.in_(["Open", "Pending"]),
        Exception_.severity == "High",
    ).all()
    
    hard_stop_count = 0
    hard_stop_rule_ids = []
    for exc in hard_stop_exceptions:
        if exc.rule_id and any(hs in exc.rule_id for hs in ["LDA_001", "REG_001", "TPA_CHAIN_GAP_001", "TPA_NOTICE_POSSESSION_001", "TPA_CAPACITY_001", "SOC_001", "SOC_002", "RUDA_001", "CANT_001"]):
            hard_stop_count += 1
            hard_stop_rule_ids.append(exc.rule_id)
    
    if hard_stop_count > 0:
        reasons.append(f"{hard_stop_count} hard-stop exception(s) open: {', '.join(hard_stop_rule_ids[:3])}")
    
    # Check pending verifications
    pending_verifs = db.query(func.count(Verification.id)).filter(
        Verification.case_id == case_id,
        Verification.org_id == org_id,
        Verification.status == "Pending",
    ).scalar() or 0
    
    if pending_verifs > 0:
        reasons.append(f"{pending_verifs} pending verification(s) remaining")
    
    # Check CP completion
    cp_satisfied = db.query(func.count(ConditionPrecedent.id)).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        or_(
            ConditionPrecedent.status == "Satisfied",
            ConditionPrecedent.status == "Waived",
            ConditionPrecedent.satisfied_at.isnot(None),
        ),
    ).scalar() or 0
    
    cp_open = db.query(func.count(ConditionPrecedent.id)).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.status == "Open",
    ).scalar() or 0
    
    cp_total = cp_satisfied + cp_open
    cp_pct = (cp_satisfied / cp_total * 100) if cp_total > 0 else 100.0
    
    if cp_pct < cp_threshold_pct:
        reasons.append(f"CP completion at {cp_pct:.1f}%, below {cp_threshold_pct}% threshold")
    
    ready = len(reasons) == 0
    
    return {
        "ready": ready,
        "reasons": reasons if not ready else ["All criteria met"],
        "metrics": {
            "open_high_exceptions": open_high,
            "pending_verifications": pending_verifs,
            "cp_completion_pct": round(cp_pct, 1),
            "cp_threshold_pct": cp_threshold_pct,
        },
    }

