"""Workbench product contract over existing CORE services."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_reviewer, require_viewer
from app.models.document import Document
from app.services.audit import log_request_event
from app.services.workbench import (
    confirm_fact,
    evaluate_matter,
    extract_facts,
    get_workbench,
    process_document,
    request_waiver,
    submit_matter,
)

router = APIRouter(prefix="/cases", tags=["workbench"])


class WaiverRequest(BaseModel):
    exception_id: str
    waiver_reason: str


class SubmitRequest(BaseModel):
    decision: str = "CONDITIONAL_PASS"
    rationale: str


class ConfirmFactRequest(BaseModel):
    field_key: str


@router.get("/{case_id}/workbench")
async def read_workbench(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = get_workbench(db, org_id=current_user.org_id, case_id=case_id)
    log_request_event(
        db,
        request=request,
        action="workbench.read",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case_id,
        case_id=case_id,
        after_json={"findings": len(payload.get("findings") or []), "documents": len(payload.get("documents") or [])},
    )
    return payload


@router.post("/{case_id}/workbench/extract")
async def workbench_extract(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = extract_facts(db, org_id=current_user.org_id, case_id=case_id, user_id=current_user.user_id)
    log_request_event(
        db,
        request=request,
        action="workbench.extract",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case_id,
        case_id=case_id,
    )
    return result


@router.post("/{case_id}/workbench/confirm-fact")
async def workbench_confirm_fact(
    request: Request,
    case_id: uuid.UUID,
    body: ConfirmFactRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    field = confirm_fact(
        db,
        org_id=current_user.org_id,
        case_id=case_id,
        field_key=body.field_key,
        user_id=current_user.user_id,
    )
    log_request_event(
        db,
        request=request,
        action="workbench.confirm_fact",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="dossier_field",
        entity_id=field.id,
        case_id=case_id,
        after_json={"field_key": field.field_key},
    )
    return {
        "field_key": field.field_key,
        "field_value": field.field_value,
        "needs_confirmation": bool(field.needs_confirmation),
    }


@router.post("/{case_id}/workbench/evaluate")
async def workbench_evaluate(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    counts = evaluate_matter(db, org_id=current_user.org_id, case_id=case_id, user_id=current_user.user_id)
    log_request_event(
        db,
        request=request,
        action="workbench.evaluate",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case_id,
        case_id=case_id,
        after_json=counts if isinstance(counts, dict) else None,
    )
    return counts if isinstance(counts, dict) else {"result": counts}


@router.post("/{case_id}/workbench/process-document/{document_id}")
async def workbench_process_document(
    request: Request,
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.case_id == case_id,
        Document.org_id == current_user.org_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    task_id = process_document(db, document=document, org_id=current_user.org_id, user_id=current_user.user_id)
    log_request_event(
        db,
        request=request,
        action="workbench.process_document",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="document",
        entity_id=document_id,
        case_id=case_id,
    )
    return {"document_id": str(document_id), "task_id": task_id}


@router.post("/{case_id}/workbench/request-waiver")
async def workbench_request_waiver(
    request: Request,
    case_id: uuid.UUID,
    body: WaiverRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    approval = request_waiver(
        db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        role=current_user.role,
        exception_id=body.exception_id,
        waiver_reason=body.waiver_reason,
    )
    log_request_event(
        db,
        request=request,
        action="workbench.request_waiver",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="approval",
        entity_id=approval.id,
        case_id=case_id,
    )
    return {"id": str(approval.id), "status": approval.status, "request_type": approval.request_type}


@router.post("/{case_id}/workbench/submit")
async def workbench_submit(
    request: Request,
    case_id: uuid.UUID,
    body: SubmitRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    approval = submit_matter(
        db,
        org_id=current_user.org_id,
        case_id=case_id,
        user_id=current_user.user_id,
        role=current_user.role,
        decision=body.decision,
        rationale=body.rationale,
    )
    log_request_event(
        db,
        request=request,
        action="workbench.submit",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="approval",
        entity_id=approval.id,
        case_id=case_id,
    )
    return {"id": str(approval.id), "status": approval.status, "request_type": approval.request_type}
