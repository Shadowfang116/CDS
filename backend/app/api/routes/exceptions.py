from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter(tags=["exceptions"])

# TEMP in-memory store so UI can wire end-to-end today.
# Replace with DB-backed service + audit log insert in next patch.
_STORE: Dict[str, dict] = {}

class EvidenceRef(BaseModel):
  doc_id: str
  page: int
  snippet: Optional[str] = None

class ExceptionOut(BaseModel):
  id: str
  severity: str
  module: str
  title: str
  description: str
  status: str
  cp_text: Optional[str] = None
  waiver_reason: Optional[str] = None
  evidence_refs: List[EvidenceRef] = []

class ResolveIn(BaseModel):
  case_id: Optional[str] = None

class WaiveIn(BaseModel):
  waiver_reason: str

def _seed_case(case_id: str) -> List[dict]:
  # Deterministic sample rows keyed by case_id so UI always has data.
  ex1 = {
    "id": f"{case_id}-ex-001",
    "severity": "high",
    "module": "Title/Ownership",
    "title": "Name mismatch in seller CNIC vs deed",
    "description": "Seller name in CNIC block does not match deed party name. Requires clarification and supporting evidence.",
    "status": "open",
    "cp_text": "Obtain affidavit/undertaking from seller and corrected/verified CNIC details, or documentary proof reconciling the name variation.",
    "waiver_reason": None,
    "evidence_refs": [
      {"doc_id": "sale-deed", "page": 1, "snippet": "فروشندہ: …"},
      {"doc_id": "cnic", "page": 1, "snippet": "Name: …"},
    ],
  }
  ex2 = {
    "id": f"{case_id}-ex-002",
    "severity": "medium",
    "module": "Society/NOC",
    "title": "Society NOC not found in annexures",
    "description": "Society NOC is required for mortgage against society plot. Not identified in uploaded annexures.",
    "status": "open",
    "cp_text": "Provide valid and current Society NOC permitting mortgage/charge in favour of the Bank.",
    "waiver_reason": None,
    "evidence_refs": [
      {"doc_id": "annexures", "page": 3, "snippet": "Annexure list…"},
    ],
  }
  for ex in (ex1, ex2):
    _STORE[ex["id"]] = ex
  return [ex1, ex2]

@router.get("/cases/{case_id}/exceptions", response_model=List[ExceptionOut])
def list_case_exceptions(case_id: str):
  # In v1: return seeded sample unless replaced by DB.
  return _seed_case(case_id)

@router.post("/exceptions/{exception_id}/resolve", response_model=ExceptionOut)
def resolve_exception(exception_id: str, _payload: ResolveIn):
  if exception_id not in _STORE:
    raise HTTPException(status_code=404, detail="exception_not_found")
  ex = _STORE[exception_id]
  ex["status"] = "resolved"
  ex["waiver_reason"] = None
  _STORE[exception_id] = ex
  return ex

@router.post("/exceptions/{exception_id}/waive", response_model=ExceptionOut)
def waive_exception(exception_id: str, payload: WaiveIn):
  if exception_id not in _STORE:
    raise HTTPException(status_code=404, detail="exception_not_found")
  ex = _STORE[exception_id]
  ex["status"] = "waived"
  ex["waiver_reason"] = payload.waiver_reason
  _STORE[exception_id] = ex
  return ex
