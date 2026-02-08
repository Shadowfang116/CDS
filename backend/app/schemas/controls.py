"""Case controls response schemas for P9."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class RegimeInfo(BaseModel):
    """Regime classification information."""
    regime: str
    confidence: float
    reasons: List[str]


class PlaybookInfo(BaseModel):
    """Active playbook information."""
    id: str
    label: str
    regimes: List[str]
    rulesets: List[str]
    hard_stops: List[str]
    required_evidence: List[dict]  # List of evidence items from playbook


class ProvidedDocument(BaseModel):
    """Document that provides evidence."""
    document_id: UUID
    filename: str
    doc_type: Optional[str]
    page_count: Optional[int]


class EvidenceChecklistItem(BaseModel):
    """Evidence checklist item with status."""
    code: str
    label: str
    acceptable_doc_types: List[str]
    provided_documents: List[ProvidedDocument]
    status: str  # "Provided" | "Missing"


class CaseRiskInfo(BaseModel):
    """Case risk information."""
    score: int
    label: str  # "Green" | "Amber" | "Red"
    open_counts: dict  # {high: int, medium: int, low: int, hard_stop: int}


class ReadinessInfo(BaseModel):
    """Case readiness information."""
    ready: bool
    blocked_reasons: List[str]


class CaseControlsResponse(BaseModel):
    """Complete case controls response."""
    case_id: UUID
    regime: RegimeInfo
    playbooks: List[PlaybookInfo]
    evidence_checklist: List[EvidenceChecklistItem]
    risk: CaseRiskInfo
    readiness: ReadinessInfo

