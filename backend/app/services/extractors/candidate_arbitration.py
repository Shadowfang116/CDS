"""Source-aware candidate arbitration.

A later document must never silently replace a better Pending candidate
from a different source. Conflicting values are preserved for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


METHOD_RANK = {
    "clause_urdu": 100,
    "label_urdu": 70,
    "label_urdu_page": 70,
    "labelled": 60,
    "section_cnic": 50,
    "urdu_marker_cnic": 50,
    "urdu_marker_direct": 50,
    "hf_extractor": 40,
    "heuristic": 30,
    "anchor": 20,
    "cnic_fallback": 15,
    "cnic_page_order": 15,
}

PARTY_FIELD_KEYS = frozenset({
    "party.seller.names",
    "party.buyer.names",
    "party.witness.names",
})


@dataclass(frozen=True)
class CandidateSnapshot:
    id: Optional[str]
    document_id: str
    field_key: str
    value: str
    confidence: float
    method: str
    status: str = "Pending"


@dataclass(frozen=True)
class ArbitrationDecision:
    action: str  # create | update_same_source | skip_downgrade | keep_conflict
    target_id: Optional[str] = None
    mark_review: bool = False
    warning: Optional[str] = None


def normalize_candidate_value(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().casefold()


def method_rank(method: Optional[str]) -> int:
    return METHOD_RANK.get((method or "").strip().lower(), 10)


def is_better(incoming: CandidateSnapshot, existing: CandidateSnapshot) -> bool:
    incoming_rank = method_rank(incoming.method)
    existing_rank = method_rank(existing.method)
    if incoming_rank != existing_rank:
        return incoming_rank > existing_rank
    return float(incoming.confidence or 0) > float(existing.confidence or 0) + 0.02


def _pending(existing: Iterable[CandidateSnapshot]) -> List[CandidateSnapshot]:
    return [row for row in existing if (row.status or "Pending") == "Pending"]


def arbitrate_candidate(
    existing: Iterable[CandidateSnapshot],
    incoming: CandidateSnapshot,
) -> ArbitrationDecision:
    """Decide whether to create, update, skip, or keep a conflicting candidate."""
    pending = _pending(existing)
    same_source = [row for row in pending if str(row.document_id) == str(incoming.document_id)]
    incoming_norm = normalize_candidate_value(incoming.value)

    if same_source:
        current = same_source[0]
        current_norm = normalize_candidate_value(current.value)
        if current_norm == incoming_norm:
            if is_better(incoming, current):
                return ArbitrationDecision("update_same_source", current.id)
            return ArbitrationDecision(
                "skip_downgrade",
                current.id,
                warning="same_source_weaker_or_equal",
            )
        if is_better(incoming, current):
            return ArbitrationDecision(
                "update_same_source",
                current.id,
                mark_review=True,
                warning="same_source_value_changed",
            )
        return ArbitrationDecision(
            "skip_downgrade",
            current.id,
            mark_review=True,
            warning="same_source_conflict_kept",
        )

    other_sources = [row for row in pending if str(row.document_id) != str(incoming.document_id)]
    if not other_sources:
        return ArbitrationDecision("create")

    matching = [
        row for row in other_sources
        if normalize_candidate_value(row.value) == incoming_norm
    ]
    if matching:
        # Corroborating source: keep both rows. Never overwrite the earlier document.
        return ArbitrationDecision("create")

    stronger_existing = [row for row in other_sources if not is_better(incoming, row)]
    warning = "conflicting_source"
    if stronger_existing and incoming.field_key in PARTY_FIELD_KEYS:
        warning = "conflicting_source_preserved"
    return ArbitrationDecision(
        "keep_conflict",
        mark_review=True,
        warning=warning,
    )
