"""Pydantic schemas for Golden Case Evaluation."""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ExpectationCreate(BaseModel):
    finding_type: str               # "exception" | "cp"
    expected_rule_id: str | None = None
    expected_title: str
    expected_severity: str | None = None
    expected_text: str | None = None
    is_critical: bool = False
    notes: str | None = None


class ExpectationUpdate(BaseModel):
    finding_type: str | None = None
    expected_rule_id: str | None = None
    expected_title: str | None = None
    expected_severity: str | None = None
    expected_text: str | None = None
    is_critical: bool | None = None
    notes: str | None = None


class ExpectationResponse(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID
    finding_type: str
    expected_rule_id: str | None = None
    expected_title: str
    expected_severity: str | None = None
    expected_text: str | None = None
    is_critical: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvaluationFindingResponse(BaseModel):
    id: UUID
    evaluation_run_id: UUID
    expectation_id: UUID | None = None
    finding_type: str
    expected_rule_id: str | None = None
    actual_rule_id: str | None = None
    expected_title: str | None = None
    actual_title: str | None = None
    expected_text: str | None = None
    actual_text: str | None = None
    expected_severity: str | None = None
    actual_severity: str | None = None
    match_status: str               # matched | missed | extra
    similarity_score: float | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class EvaluationRunResponse(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    critical_recall: float | None = None
    overall_recall: float | None = None
    precision: float | None = None
    expected_count: int
    matched_count: int
    missed_count: int
    extra_count: int
    status: str
    created_by: UUID
    error_message: str | None = None
    findings: list[EvaluationFindingResponse] = []

    class Config:
        from_attributes = True


class EvaluationRunListItem(BaseModel):
    id: UUID
    org_id: UUID
    case_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    critical_recall: float | None = None
    overall_recall: float | None = None
    precision: float | None = None
    expected_count: int
    matched_count: int
    missed_count: int
    extra_count: int
    status: str
    created_by: UUID
    error_message: str | None = None

    class Config:
        from_attributes = True
