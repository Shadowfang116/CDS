"""Rules, exceptions, and CP endpoints."""
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_reviewer, require_viewer
from app.core.roles import role_satisfies
from app.db.session import get_db
from app.models.case import Case
from app.models.cp_evidence import CPEvidenceRef
from app.models.rules import ConditionPrecedent, Exception_, ExceptionEvidenceRef
from app.services.audit import log_request_event
from app.services.rule_engine import run_rules

router = APIRouter(tags=["rules"])

SEVERITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}
EXCEPTION_STATUS_MAP = {
    "open": "Open",
    "resolved": "Resolved",
    "waived": "Waived",
    "waive": "Waived",
}
CP_STATUS_MAP = {
    "open": "Open",
    "met": "Met",
    "satisfied": "Met",
    "waived": "Waived",
}


class EvidenceRefPayload(BaseModel):
    document_id: str | None = None
    page_number: int | None = None
    note: str | None = None


class ExceptionResponse(BaseModel):
    id: str
    case_id: str
    org_id: str
    severity: str
    module: str
    title: str
    description: str | None = None
    evidence_refs: list[dict[str, Any]] = []
    cp_text: str | None = None
    resolution_conditions: str | None = None
    status: str
    waiver_reason: str | None = None
    rule_id: str | None = None
    is_manual: bool
    source_document_id: str | None = None
    source_page: int | None = None
    created_at: datetime
    updated_at: datetime


class ExceptionsListResponse(BaseModel):
    case_id: str
    total: int
    high_count: int
    medium_count: int
    low_count: int
    open_count: int
    resolved_count: int
    waived_count: int
    exceptions: list[ExceptionResponse]


class CPResponse(BaseModel):
    id: str
    case_id: str
    org_id: str
    severity: str
    text: str
    evidence_required: str | None = None
    due_date: datetime | None = None
    status: str
    waiver_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    evidence_refs: list[dict[str, Any]] = []


class CPsListResponse(BaseModel):
    case_id: str
    total: int
    open_count: int
    satisfied_count: int
    waived_count: int
    cps: list[CPResponse]


class ExceptionCreateRequest(BaseModel):
    severity: str
    module: str
    title: str
    description: str
    evidence_refs: list[EvidenceRefPayload] = Field(default_factory=list)
    cp_text: str | None = None
    resolution_conditions: str | None = None
    rule_id: str | None = None
    source_document_id: str | None = None
    source_page: int | None = None


class ExceptionUpdateRequest(BaseModel):
    severity: str | None = None
    module: str | None = None
    title: str | None = None
    description: str | None = None
    evidence_refs: list[EvidenceRefPayload] | None = None
    cp_text: str | None = None
    resolution_conditions: str | None = None
    status: str | None = None
    action: str | None = None
    reason: str | None = None
    waiver_reason: str | None = None
    source_document_id: str | None = None
    source_page: int | None = None


class CPStatusUpdateRequest(BaseModel):
    status: str
    waiver_reason: str | None = None


class EvaluateResponse(BaseModel):
    case_id: str
    critical: int = 0
    high: int
    medium: int
    low: int
    total: int
    cps_total: int


def _normalize_severity(value: str) -> str:
    canonical = SEVERITY_MAP.get(value.strip().lower())
    if not canonical:
        raise HTTPException(status_code=422, detail="severity must be one of critical, high, medium, low")
    return canonical


def _normalize_exception_status(value: str) -> str:
    canonical = EXCEPTION_STATUS_MAP.get(value.strip().lower())
    if not canonical:
        raise HTTPException(status_code=422, detail="status must be one of open, resolved, waived")
    return canonical


def _normalize_cp_status(value: str) -> str:
    canonical = CP_STATUS_MAP.get(value.strip().lower())
    if not canonical:
        raise HTTPException(status_code=422, detail="status must be one of open, met, waived")
    return canonical


def _get_case_or_404(db: Session, *, case_id: uuid.UUID, org_id: uuid.UUID) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _get_exception_or_404(db: Session, *, exception_id: uuid.UUID, org_id: uuid.UUID) -> Exception_:
    exception_item = (
        db.query(Exception_)
        .filter(Exception_.id == exception_id, Exception_.org_id == org_id)
        .first()
    )
    if not exception_item:
        raise HTTPException(status_code=404, detail="Exception not found")
    return exception_item


def _get_cp_or_404(db: Session, *, cp_id: uuid.UUID, org_id: uuid.UUID) -> ConditionPrecedent:
    cp = db.query(ConditionPrecedent).filter(ConditionPrecedent.id == cp_id, ConditionPrecedent.org_id == org_id).first()
    if not cp:
        raise HTTPException(status_code=404, detail="CP not found")
    return cp


def _serialize_exception_refs(db: Session, exception_item: Exception_) -> list[dict[str, Any]]:
    if exception_item.evidence_refs:
        return exception_item.evidence_refs
    refs = (
        db.query(ExceptionEvidenceRef)
        .filter(
            ExceptionEvidenceRef.exception_id == exception_item.id,
            ExceptionEvidenceRef.org_id == exception_item.org_id,
        )
        .all()
    )
    return [
        {
            "id": str(ref.id),
            "document_id": str(ref.document_id) if ref.document_id else None,
            "page_number": ref.page_number,
            "note": ref.note,
        }
        for ref in refs
    ]


def _serialize_exception(db: Session, exception_item: Exception_) -> ExceptionResponse:
    return ExceptionResponse(
        id=str(exception_item.id),
        case_id=str(exception_item.case_id),
        org_id=str(exception_item.org_id),
        severity=exception_item.severity,
        module=exception_item.module,
        title=exception_item.title,
        description=exception_item.description,
        evidence_refs=_serialize_exception_refs(db, exception_item),
        cp_text=exception_item.cp_text,
        resolution_conditions=exception_item.resolution_conditions,
        status=exception_item.status,
        waiver_reason=exception_item.waiver_reason,
        rule_id=exception_item.rule_id,
        is_manual=bool(exception_item.is_manual),
        source_document_id=str(exception_item.source_document_id) if exception_item.source_document_id else None,
        source_page=exception_item.source_page,
        created_at=exception_item.created_at,
        updated_at=exception_item.updated_at,
    )


def _serialize_cp_evidence(db: Session, cp: ConditionPrecedent) -> list[dict[str, Any]]:
    refs = (
        db.query(CPEvidenceRef)
        .filter(CPEvidenceRef.cp_id == cp.id, CPEvidenceRef.org_id == cp.org_id)
        .all()
    )
    return [
        {
            "id": str(ref.id),
            "document_id": str(ref.document_id) if ref.document_id else None,
            "page_number": ref.page_number,
            "note": ref.note,
        }
        for ref in refs
    ]


def _serialize_cp(db: Session, cp: ConditionPrecedent) -> CPResponse:
    return CPResponse(
        id=str(cp.id),
        case_id=str(cp.case_id),
        org_id=str(cp.org_id),
        severity=cp.severity,
        text=cp.text,
        evidence_required=cp.evidence_required,
        due_date=cp.due_date,
        status="Met" if cp.status == "Satisfied" else cp.status,
        waiver_reason=cp.waiver_reason,
        created_at=cp.created_at,
        updated_at=cp.updated_at,
        evidence_refs=_serialize_cp_evidence(db, cp),
    )


@router.post("/cases/{case_id}/evaluate", response_model=EvaluateResponse)
async def evaluate_case(
    request: Request,
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(db, case_id=case_id, org_id=current_user.org_id)
    raw_counts = run_rules(db, current_user.org_id, case_id, current_user.user_id)
    counts = {
        "critical": int(raw_counts.get("critical", 0)),
        "high": int(raw_counts.get("high", 0)),
        "medium": int(raw_counts.get("medium", 0)),
        "low": int(raw_counts.get("low", 0)),
        "total": int(raw_counts.get("total", 0)),
        "cps_total": int(raw_counts.get("cps_total", 0)),
    }
    log_request_event(
        db,
        request=request,
        action="rules.evaluate",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="case",
        entity_id=case.id,
        case_id=case.id,
        after_json=counts,
    )
    return EvaluateResponse(case_id=str(case_id), **counts)


@router.get("/cases/{case_id}/exceptions", response_model=ExceptionsListResponse)
async def list_exceptions(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _get_case_or_404(db, case_id=case_id, org_id=current_user.org_id)
    exceptions = (
        db.query(Exception_)
        .filter(Exception_.case_id == case_id, Exception_.org_id == current_user.org_id)
        .order_by(Exception_.created_at.desc())
        .all()
    )
    response_items = [_serialize_exception(db, exception_item) for exception_item in exceptions]
    return ExceptionsListResponse(
        case_id=str(case_id),
        total=len(response_items),
        high_count=sum(1 for item in response_items if item.severity == "High"),
        medium_count=sum(1 for item in response_items if item.severity == "Medium"),
        low_count=sum(1 for item in response_items if item.severity == "Low"),
        open_count=sum(1 for item in response_items if item.status == "Open"),
        resolved_count=sum(1 for item in response_items if item.status == "Resolved"),
        waived_count=sum(1 for item in response_items if item.status == "Waived"),
        exceptions=response_items,
    )


@router.post("/cases/{case_id}/exceptions", response_model=ExceptionResponse, status_code=status.HTTP_201_CREATED)
async def create_exception(
    request: Request,
    case_id: uuid.UUID,
    body: ExceptionCreateRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    _get_case_or_404(db, case_id=case_id, org_id=current_user.org_id)
    exception_item = Exception_(
        org_id=current_user.org_id,
        case_id=case_id,
        severity=_normalize_severity(body.severity),
        module=body.module,
        title=body.title,
        description=body.description,
        evidence_refs=[item.model_dump() for item in body.evidence_refs],
        cp_text=body.cp_text,
        resolution_conditions=body.resolution_conditions,
        status="Open",
        rule_id=body.rule_id,
        is_manual=True,
        source_document_id=uuid.UUID(body.source_document_id) if body.source_document_id else None,
        source_page=body.source_page,
    )
    db.add(exception_item)
    db.commit()
    db.refresh(exception_item)
    log_request_event(
        db,
        request=request,
        action="exception.create",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="exception",
        entity_id=exception_item.id,
        case_id=case_id,
        after_json={"title": exception_item.title, "severity": exception_item.severity, "status": exception_item.status},
    )
    return _serialize_exception(db, exception_item)


@router.get("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def get_exception(
    exception_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    exception_item = _get_exception_or_404(db, exception_id=exception_id, org_id=current_user.org_id)
    return _serialize_exception(db, exception_item)


@router.put("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def update_exception_record(
    request: Request,
    exception_id: uuid.UUID,
    body: ExceptionUpdateRequest,
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    exception_item = _get_exception_or_404(db, exception_id=exception_id, org_id=current_user.org_id)
    before_json = _serialize_exception(db, exception_item).model_dump(mode="json")

    if body.severity is not None:
        exception_item.severity = _normalize_severity(body.severity)
    if body.module is not None:
        exception_item.module = body.module
    if body.title is not None:
        exception_item.title = body.title
    if body.description is not None:
        exception_item.description = body.description
    if body.evidence_refs is not None:
        exception_item.evidence_refs = [item.model_dump() for item in body.evidence_refs]
    if body.cp_text is not None:
        exception_item.cp_text = body.cp_text
    if body.resolution_conditions is not None:
        exception_item.resolution_conditions = body.resolution_conditions
    if body.source_document_id is not None:
        exception_item.source_document_id = uuid.UUID(body.source_document_id) if body.source_document_id else None
    if body.source_page is not None:
        exception_item.source_page = body.source_page

    db.commit()
    db.refresh(exception_item)
    log_request_event(
        db,
        request=request,
        action="exception.update",
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="exception",
        entity_id=exception_item.id,
        case_id=exception_item.case_id,
        before_json=before_json,
        after_json=_serialize_exception(db, exception_item).model_dump(mode="json"),
    )
    return _serialize_exception(db, exception_item)


@router.patch("/exceptions/{exception_id}", response_model=ExceptionResponse)
async def update_exception_status(
    request: Request,
    exception_id: uuid.UUID,
    body: ExceptionUpdateRequest,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    exception_item = _get_exception_or_404(db, exception_id=exception_id, org_id=current_user.org_id)
    requested_state = body.status or body.action
    if not requested_state:
        raise HTTPException(status_code=422, detail="status or action is required")

    normalized_status = _normalize_exception_status(requested_state)
    closure_reason = (body.reason or "").strip() or None
    waiver_reason = (body.waiver_reason or body.reason or "").strip() or None
    if normalized_status in {"Resolved", "Open"} and not role_satisfies(current_user.role, "Reviewer"):
        raise HTTPException(
            status_code=403,
            detail="Reviewer role required to resolve or reopen exceptions",
        )
    if normalized_status == "Waived" and not role_satisfies(current_user.role, "Approver"):
        raise HTTPException(status_code=403, detail="Approver role required to waive exceptions")
    if normalized_status == "Waived" and waiver_reason is None:
        raise HTTPException(status_code=422, detail="waiver_reason is required when waiving an exception")

    before_json = _serialize_exception(db, exception_item).model_dump(mode="json")
    exception_item.status = normalized_status
    if normalized_status == "Resolved":
        exception_item.resolved_by_user_id = current_user.user_id
        exception_item.resolved_at = datetime.utcnow()
        exception_item.waiver_reason = None
        exception_item.waived_by_user_id = None
        exception_item.waived_at = None
        audit_action = "exception.resolve"
    elif normalized_status == "Waived":
        exception_item.waiver_reason = waiver_reason
        exception_item.waived_by_user_id = current_user.user_id
        exception_item.waived_at = datetime.utcnow()
        exception_item.resolved_by_user_id = None
        exception_item.resolved_at = None
        audit_action = "exception.waive"
    else:
        exception_item.resolved_by_user_id = None
        exception_item.resolved_at = None
        exception_item.waived_by_user_id = None
        exception_item.waived_at = None
        exception_item.waiver_reason = None
        audit_action = "exception.reopen"
    db.commit()
    db.refresh(exception_item)
    after_json = _serialize_exception(db, exception_item).model_dump(mode="json")
    if normalized_status == "Resolved" and closure_reason is not None:
        after_json["reason"] = closure_reason
    if normalized_status == "Waived" and waiver_reason is not None:
        after_json["reason"] = waiver_reason

    log_request_event(
        db,
        request=request,
        action=audit_action,
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="exception",
        entity_id=exception_item.id,
        case_id=exception_item.case_id,
        before_json=before_json,
        after_json=after_json,
    )
    return _serialize_exception(db, exception_item)


class ExceptionWaiveRequest(BaseModel):
    waiver_reason: str


@router.post("/exceptions/{exception_id}/waive", response_model=ExceptionResponse)
async def waive_exception(
    request: Request,
    exception_id: uuid.UUID,
    body: ExceptionWaiveRequest,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Dedicated waive endpoint — Approver only."""
    return await update_exception_status(
        request=request,
        exception_id=exception_id,
        body=ExceptionUpdateRequest(action="waived", waiver_reason=body.waiver_reason),
        current_user=current_user,
        db=db,
    )


@router.get("/cases/{case_id}/cps", response_model=CPsListResponse)
async def list_cps(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    _get_case_or_404(db, case_id=case_id, org_id=current_user.org_id)
    cps = (
        db.query(ConditionPrecedent)
        .filter(ConditionPrecedent.case_id == case_id, ConditionPrecedent.org_id == current_user.org_id)
        .order_by(ConditionPrecedent.created_at.desc())
        .all()
    )
    response_items = [_serialize_cp(db, cp) for cp in cps]
    return CPsListResponse(
        case_id=str(case_id),
        total=len(response_items),
        open_count=sum(1 for cp in response_items if cp.status == "Open"),
        satisfied_count=sum(1 for cp in response_items if cp.status == "Met"),
        waived_count=sum(1 for cp in response_items if cp.status == "Waived"),
        cps=response_items,
    )


@router.patch("/cps/{cp_id}", response_model=CPResponse)
async def update_cp_status(
    request: Request,
    cp_id: uuid.UUID,
    body: CPStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    cp = _get_cp_or_404(db, cp_id=cp_id, org_id=current_user.org_id)
    next_status = _normalize_cp_status(body.status)
    waiver_reason = (body.waiver_reason or "").strip() or None
    if next_status == "Waived":
        if not role_satisfies(current_user.role, "Approver"):
            raise HTTPException(status_code=403, detail="Approver role required to waive Conditions Precedent")
        if waiver_reason is None:
            raise HTTPException(status_code=422, detail="waiver_reason is required when waiving a Condition Precedent")
    elif not role_satisfies(current_user.role, "Reviewer"):
        raise HTTPException(status_code=403, detail="Reviewer role required to update Conditions Precedent")

    before_json = _serialize_cp(db, cp).model_dump(mode="json")
    cp.status = "Satisfied" if next_status == "Met" else next_status
    if cp.status == "Satisfied":
        cp.satisfied_at = datetime.utcnow()
        cp.satisfied_by_user_id = current_user.user_id
        cp.waiver_reason = None
        cp.waived_at = None
        cp.waived_by_user_id = None
        audit_action = "cp.status_changed"
    elif cp.status == "Waived":
        cp.waiver_reason = waiver_reason
        cp.waived_at = datetime.utcnow()
        cp.waived_by_user_id = current_user.user_id
        cp.satisfied_at = None
        cp.satisfied_by_user_id = None
        audit_action = "cp.waive"
    else:
        cp.satisfied_at = None
        cp.satisfied_by_user_id = None
        cp.waiver_reason = None
        cp.waived_at = None
        cp.waived_by_user_id = None
        audit_action = "cp.status_changed"
    db.commit()
    db.refresh(cp)
    log_request_event(
        db,
        request=request,
        action=audit_action,
        org_id=current_user.org_id,
        actor_id=current_user.user_id,
        entity_type="cp",
        entity_id=cp.id,
        case_id=cp.case_id,
        before_json=before_json,
        after_json=_serialize_cp(db, cp).model_dump(mode="json"),
    )
    return _serialize_cp(db, cp)
