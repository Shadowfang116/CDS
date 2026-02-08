"""Dashboard response schemas."""
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    """Key Performance Indicators for the dashboard."""
    active_cases: int
    open_high_exceptions: int
    cp_completion_pct: float
    verification_completion_pct: float


class NeedsAttentionItem(BaseModel):
    """A case that needs attention."""
    case_id: UUID
    title: str
    status: str
    open_high: int
    open_medium: int
    open_low: int
    pending_verifications: int
    updated_at: datetime


class ActivityItem(BaseModel):
    """Recent activity/audit log item."""
    created_at: datetime
    actor_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None


class TimeseriesEntry(BaseModel):
    """Daily timeseries data point."""
    date: str  # YYYY-MM-DD
    cases_created: int
    exports_generated: int
    high_exceptions_created: int


class ExceptionsBySeverity(BaseModel):
    """Open exceptions grouped by severity."""
    high: int
    medium: int
    low: int


class ApprovalPreviewItem(BaseModel):
    """Preview item for pending approvals."""
    id: UUID
    request_type: str
    request_type_label: str
    case_title: str
    created_at: datetime


class ReadyForApprovalItem(BaseModel):
    """Case ready for final approval."""
    case_id: UUID
    title: str
    status: str
    cp_completion_pct: float
    updated_at: datetime


class DashboardResponse(BaseModel):
    """Full dashboard response."""
    range_days: int
    kpis: DashboardKPIs
    cases_by_status: Dict[str, int]
    exceptions_by_severity: ExceptionsBySeverity
    timeseries: List[TimeseriesEntry]
    needs_attention: List[NeedsAttentionItem]
    recent_activity: List[ActivityItem]
    # Phase 8: Approvals overlay
    approvals_pending_count: int = 0
    approvals_pending_preview: List[ApprovalPreviewItem] = []
    ready_for_approval_count: int = 0
    ready_for_approval_list: List[ReadyForApprovalItem] = []


# Cohort endpoint schemas
class CohortFilters(BaseModel):
    """Filters applied to cohort query."""
    severity: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None


class CohortCaseItem(BaseModel):
    """A case in the cohort result."""
    case_id: UUID
    title: str
    status: str
    updated_at: datetime
    open_high: int
    open_medium: int
    open_low: int
    pending_verifications: int


class CohortActivityItem(BaseModel):
    """An enriched activity item for cohort result."""
    created_at: datetime
    actor_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    case_title: Optional[str] = None


class CohortCounts(BaseModel):
    """Counts summary for cohort."""
    cases: int
    activity: int


class CohortResponse(BaseModel):
    """Cohort endpoint response."""
    range_days: int
    filters: CohortFilters
    cases: List[CohortCaseItem]
    activity: List[CohortActivityItem]
    counts: CohortCounts


# Saved Views schemas
class SavedViewConfig(BaseModel):
    """Configuration stored in a saved view."""
    days: int = 30
    severity: Optional[str] = None
    status: Optional[str] = None


class SavedViewCreate(BaseModel):
    """Request to create a saved view."""
    name: str
    config_json: SavedViewConfig
    is_default: bool = False
    visibility: str = "private"  # "private" | "org"
    shared_with_roles: List[str] = []  # Empty means all roles when visibility=org


class SavedViewUpdate(BaseModel):
    """Request to update a saved view."""
    name: Optional[str] = None
    config_json: Optional[SavedViewConfig] = None
    is_default: Optional[bool] = None
    visibility: Optional[str] = None
    shared_with_roles: Optional[List[str]] = None


class SavedViewResponse(BaseModel):
    """Saved view response."""
    id: UUID
    name: str
    is_default: bool
    config_json: SavedViewConfig
    visibility: str
    shared_with_roles: List[str]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None


# Cohort Export response
class CohortExportResponse(BaseModel):
    """Response after creating a cohort export."""
    export_id: UUID
    filename: str
    url: str
    expires_in_seconds: int
    created_at: datetime
    row_count: int


# Case Insights schemas
class CaseInsightsSummary(BaseModel):
    """Summary statistics for a case."""
    open_exceptions_high: int
    open_exceptions_medium: int
    open_exceptions_low: int
    cp_completion_pct: float
    verification_completion_pct: float
    exports_generated: int
    last_rule_run_at: Optional[datetime] = None
    last_ocr_at: Optional[datetime] = None


class CaseInsightsTimeseries(BaseModel):
    """Daily activity data for a case."""
    date: str  # YYYY-MM-DD
    exceptions_opened: int
    exceptions_resolved: int
    cps_satisfied: int
    verifications_verified: int
    exports_generated: int
    rule_evaluations: int
    ocr_pages_done: int


class CaseInsightsResponse(BaseModel):
    """Full case insights response."""
    case_id: UUID
    range_days: int
    summary: CaseInsightsSummary
    timeseries: List[CaseInsightsTimeseries]


# Digest schemas
class DigestFiltersConfig(BaseModel):
    """Filters for digest generation."""
    days: int = 30
    severity: Optional[str] = None
    status: Optional[str] = None


class DigestScheduleCreate(BaseModel):
    """Request to create a digest schedule."""
    name: str
    cadence: str = "weekly"  # "daily" | "weekly"
    hour_local: int = 9
    weekday: Optional[int] = None  # 0=Monday, required if weekly
    is_enabled: bool = True
    filters_json: DigestFiltersConfig = DigestFiltersConfig()


class DigestScheduleUpdate(BaseModel):
    """Request to update a digest schedule."""
    name: Optional[str] = None
    cadence: Optional[str] = None
    hour_local: Optional[int] = None
    weekday: Optional[int] = None
    is_enabled: Optional[bool] = None
    filters_json: Optional[DigestFiltersConfig] = None


class DigestScheduleResponse(BaseModel):
    """Digest schedule response."""
    id: UUID
    name: str
    cadence: str
    hour_local: int
    weekday: Optional[int]
    is_enabled: bool
    filters_json: DigestFiltersConfig
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class DigestRunResponse(BaseModel):
    """Digest run record response."""
    id: UUID
    schedule_id: UUID
    run_at: datetime
    status: str
    output_export_id: Optional[UUID] = None
    error_message: Optional[str] = None
    created_at: datetime


class DigestRunNowResponse(BaseModel):
    """Response from run-now endpoint."""
    run_id: UUID
    status: str
    message: str
