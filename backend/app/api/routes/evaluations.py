"""P30: Golden Case Evaluation API routes."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_reviewer, require_role, require_tenant_scope, require_viewer
from app.db.session import get_db
from app.models.case import Case
from app.models.evaluation import EvaluationFinding, EvaluationRun, GoldenCaseExpectation
from app.schemas.evaluation import (
    EvaluationFindingResponse,
    EvaluationRunListItem,
    EvaluationRunResponse,
    ExpectationCreate,
    ExpectationResponse,
    ExpectationUpdate,
)
from app.services.audit import write_audit_event
from app.services.evaluation_service import run_evaluation

router = APIRouter(tags=["evaluations"])


def _get_case_or_404(db: Session, case_id: uuid.UUID, org_id: uuid.UUID) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.org_id == org_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _load_findings(db: Session, run_id: uuid.UUID) -> list[EvaluationFindingResponse]:
    rows = (
        db.query(EvaluationFinding)
        .filter(EvaluationFinding.evaluation_run_id == run_id)
        .all()
    )
    return [EvaluationFindingResponse.model_validate(f) for f in rows]


# ---------------------------------------------------------------------------
# Evaluation runs
# ---------------------------------------------------------------------------

@router.post(
    "/cases/{case_id}/evaluations/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_evaluation_run(
    request: Request,
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """Trigger a new evaluation run for a case (Admin / Reviewer)."""
    _get_case_or_404(db, case_id, org_id)

    eval_run = run_evaluation(db=db, org_id=org_id, case_id=case_id, created_by=current_user.user_id)

    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="evaluation.run",
        entity_type="evaluation_run",
        entity_id=eval_run.id,
        event_metadata={"case_id": str(case_id), "status": eval_run.status},
        request_id=getattr(request.state, "request_id", None),
    )

    result = EvaluationRunResponse.model_validate(eval_run)
    result.findings = _load_findings(db, eval_run.id)
    return result


@router.get("/cases/{case_id}/evaluations/latest", response_model=EvaluationRunResponse)
async def get_latest_evaluation(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Return the most recent evaluation run for a case."""
    _get_case_or_404(db, case_id, org_id)

    eval_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.org_id == org_id, EvaluationRun.case_id == case_id)
        .order_by(EvaluationRun.started_at.desc())
        .first()
    )
    if not eval_run:
        raise HTTPException(status_code=404, detail="No evaluation runs found for this case")

    result = EvaluationRunResponse.model_validate(eval_run)
    result.findings = _load_findings(db, eval_run.id)
    return result


@router.get("/cases/{case_id}/evaluations/history", response_model=list[EvaluationRunListItem])
async def list_evaluation_history(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List all evaluation runs for a case, newest first."""
    _get_case_or_404(db, case_id, org_id)

    runs = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.org_id == org_id, EvaluationRun.case_id == case_id)
        .order_by(EvaluationRun.started_at.desc())
        .all()
    )
    return [EvaluationRunListItem.model_validate(r) for r in runs]


# ---------------------------------------------------------------------------
# Expectations
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/expectations", response_model=list[ExpectationResponse])
async def list_expectations(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List all golden-standard expectations for a case."""
    _get_case_or_404(db, case_id, org_id)

    rows = (
        db.query(GoldenCaseExpectation)
        .filter(
            GoldenCaseExpectation.org_id == org_id,
            GoldenCaseExpectation.case_id == case_id,
        )
        .order_by(GoldenCaseExpectation.created_at.asc())
        .all()
    )
    return [ExpectationResponse.model_validate(e) for e in rows]


@router.post(
    "/cases/{case_id}/expectations",
    response_model=ExpectationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_expectation(
    request: Request,
    case_id: uuid.UUID,
    payload: ExpectationCreate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Create a golden-standard expectation (Admin only)."""
    if payload.finding_type not in ("exception", "cp"):
        raise HTTPException(status_code=400, detail="finding_type must be 'exception' or 'cp'")

    _get_case_or_404(db, case_id, org_id)

    exp = GoldenCaseExpectation(
        org_id=org_id,
        case_id=case_id,
        finding_type=payload.finding_type,
        expected_rule_id=payload.expected_rule_id,
        expected_title=payload.expected_title,
        expected_severity=payload.expected_severity,
        expected_text=payload.expected_text,
        is_critical=payload.is_critical,
        notes=payload.notes,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="evaluation.expectation.create",
        entity_type="golden_case_expectation",
        entity_id=exp.id,
        event_metadata={"case_id": str(case_id), "finding_type": payload.finding_type},
        request_id=getattr(request.state, "request_id", None),
    )

    return ExpectationResponse.model_validate(exp)


@router.put("/expectations/{expectation_id}", response_model=ExpectationResponse)
async def update_expectation(
    request: Request,
    expectation_id: uuid.UUID,
    payload: ExpectationUpdate,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Update a golden-standard expectation (Admin only)."""
    exp = (
        db.query(GoldenCaseExpectation)
        .filter(
            GoldenCaseExpectation.id == expectation_id,
            GoldenCaseExpectation.org_id == org_id,
        )
        .first()
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Expectation not found")

    if payload.finding_type is not None:
        if payload.finding_type not in ("exception", "cp"):
            raise HTTPException(status_code=400, detail="finding_type must be 'exception' or 'cp'")
        exp.finding_type = payload.finding_type
    if payload.expected_rule_id is not None:
        exp.expected_rule_id = payload.expected_rule_id
    if payload.expected_title is not None:
        exp.expected_title = payload.expected_title
    if payload.expected_severity is not None:
        exp.expected_severity = payload.expected_severity
    if payload.expected_text is not None:
        exp.expected_text = payload.expected_text
    if payload.is_critical is not None:
        exp.is_critical = payload.is_critical
    if payload.notes is not None:
        exp.notes = payload.notes

    db.commit()
    db.refresh(exp)

    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="evaluation.expectation.update",
        entity_type="golden_case_expectation",
        entity_id=exp.id,
        event_metadata={"case_id": str(exp.case_id)},
        request_id=getattr(request.state, "request_id", None),
    )

    return ExpectationResponse.model_validate(exp)


@router.delete("/expectations/{expectation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expectation(
    request: Request,
    expectation_id: uuid.UUID,
    org_id: uuid.UUID = Depends(require_tenant_scope),
    current_user: CurrentUser = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Delete a golden-standard expectation (Admin only)."""
    exp = (
        db.query(GoldenCaseExpectation)
        .filter(
            GoldenCaseExpectation.id == expectation_id,
            GoldenCaseExpectation.org_id == org_id,
        )
        .first()
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Expectation not found")

    case_id = exp.case_id
    db.delete(exp)
    db.commit()

    write_audit_event(
        db=db,
        org_id=org_id,
        actor_user_id=current_user.user_id,
        action="evaluation.expectation.delete",
        entity_type="golden_case_expectation",
        entity_id=expectation_id,
        event_metadata={"case_id": str(case_id)},
        request_id=getattr(request.state, "request_id", None),
    )
