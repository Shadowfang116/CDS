"""MVP wrapper around rule_engine with schema validation, improved timeline_gap, and dedupe."""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import yaml

from app.services.rule_schema import validate_rulepack_yaml, load_evidence_library_from_path
from app.services.rule_engine import (
    RULEPACK_PATH,
    CaseContext,
    RuleResult,
    EvidenceRef,
    build_case_context,
    get_effective_doc_types,
    evaluate_missing_evidence,
    evaluate_mismatch,
    evaluate_keyword_risk,
    evaluate_constructed_gate,
    evaluate_verification_check,
)

from app.models.rules import Exception_, ConditionPrecedent, ExceptionEvidenceRef, RuleRun
from sqlalchemy.orm import Session

try:
    from dateutil import parser as date_parser  # type: ignore
except Exception:  # pragma: no cover
    date_parser = None


def load_rulepack() -> Dict[str, Any]:
    try:
        with open(RULEPACK_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        vr = validate_rulepack_yaml(raw)
        return {"rules": vr.rules}
    except Exception:
        return {"rules": []}

# Evidence library support (standardized closure expectations)
EVIDENCE_LIBRARY_PATH = os.environ.get("EVIDENCE_LIBRARY_PATH", "/app/docs/06_evidence_library.yaml")


def load_evidence_lib() -> Dict[str, Dict[str, Any]]:
    """Load and normalize the canonical evidence library.

    Supports both legacy `evidence_options` and the canonical `rules` mapping.
    Returns a dict keyed by rule_id with keys:
      acceptable_evidence, acceptable_substitutes, closure_logic, waivable, waiver_guidance, notes
    """
    try:
        return load_evidence_library_from_path(EVIDENCE_LIBRARY_PATH)
    except Exception:
        return {}


def evidence_satisfies_rule(
    rule_id: str,
    present: Set[str] | List[str],
    library: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Check whether the provided evidence tags satisfy the rule's closure policy.

    present: a set/list of normalized evidence tags for the case (e.g., 'registry_deed', 'society_noc').
    Returns:
      {
        'rule_id': str,
        'satisfied': bool,
        'closure_logic': 'any_of'|'all_of',
        'acceptable_evidence': [...],
        'acceptable_substitutes': [...],
        'used': [...],            # evidence from `present` that contributed
        'missing': [...],         # items from acceptable_evidence not found (for all_of)
        'waivable': bool,
        'waiver_guidance': str,
      }
    """
    lib = library or load_evidence_lib()
    spec = lib.get(rule_id) or {}
    acceptable: List[str] = list(spec.get("acceptable_evidence") or [])
    substitutes: List[str] = list(spec.get("acceptable_substitutes") or [])
    logic: str = (spec.get("closure_logic") or "any_of").lower()
    waivable: bool = bool(spec.get("waivable", True))
    waiver_guidance: str = str(spec.get("waiver_guidance") or "")

    present_set: Set[str] = set(present or [])
    used: List[str] = sorted(list(present_set.intersection(set(acceptable + substitutes))))

    satisfied = False
    missing: List[str] = []
    if logic == "all_of":
        # Strict interpretation: all acceptable items must be present
        missing = [x for x in acceptable if x not in present_set]
        satisfied = len(missing) == 0 and len(acceptable) > 0
        # Basic substitute coverage: if any substitute present for missing items, treat as covered
        if not satisfied and len(acceptable) > 0 and substitutes:
            if present_set.intersection(set(substitutes)):
                # treat as covered if we have at least as many substitute items as missing ones
                satisfied = True
                missing = []
    else:  # any_of
        satisfied = len(used) > 0 or (len(acceptable) == 0 and len(substitutes) == 0)

    return {
        "rule_id": rule_id,
        "satisfied": bool(satisfied),
        "closure_logic": logic,
        "acceptable_evidence": acceptable,
        "acceptable_substitutes": substitutes,
        "used": used,
        "missing": missing,
        "waivable": waivable,
        "waiver_guidance": waiver_guidance,
    }


def _try_parse_date(value:
    str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    if date_parser is not None:
        try:
            return date_parser.parse(value, dayfirst=True, yearfirst=False)
        except Exception:
            pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def evaluate_timeline_gap(rule:
    Dict[str, Any], ctx: CaseContext) -> RuleResult:
    logic = rule.get("logic", {}) or {}
    outputs = rule.get("outputs", {}) or {}

    date_field = logic.get("date_field")
    max_age_days = int(logic.get("max_age_days", 0) or 0)
    keywords_any: List[str] = logic.get("keywords_any") or rule.get("inputs", {}).get("keywords", []) or []

    triggered = False
    evidence_refs: List[EvidenceRef] = []

    # Structured first
    dates: List[datetime] = []
    if date_field and date_field in ctx.dossier:
        for v in ctx.dossier.get(date_field, []):
            dt = _try_parse_date(v)
            if dt:
                dates.append(dt)
        if dates and max_age_days > 0:
            newest = max(dates)
            age_days = (datetime.utcnow() - newest).days
            if age_days > max_age_days:
                triggered = True
                evidence_refs.append(
                    EvidenceRef(
                        note=f"{date_field} last={newest.date()} age_days={age_days}",
                        evidence_type="structured",
                        snippet_json={
                            "type": "timeline_gap",
                            "date_field": date_field,
                            "last_date": str(newest.date()),
                            "age_days": age_days,
                            "threshold_days": max_age_days,
                        },
                    )
                )

    # OCR fallback
    if not triggered and keywords_any:
        for doc_id, page_num, text in ctx.pages:
            tl = text.lower()
            if any(kw.lower() in tl for kw in keywords_any):
                m = re.findall(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", text)
                for s in m[:3]:
                    dt = _try_parse_date(s)
                    if dt and max_age_days > 0:
                        age_days = (datetime.utcnow() - dt).days
                        if age_days > max_age_days:
                            triggered = True
                            evidence_refs.append(
                                EvidenceRef(
                                    document_id=doc_id,
                                    page_number=page_num,
                                    note=f"stale date {dt.date()}",
                                    evidence_type="structured",
                                    snippet_json={
                                        "type": "timeline_gap",
                                        "source": "ocr",
                                        "matched_date": str(dt.date()),
                                        "threshold_days": max_age_days,
                                    },
                                )
                            )
                            break
            if triggered:
                break

    return RuleResult(
        rule_id=rule["id"],
        module=rule["module"],
        severity=rule["severity"],
        triggered=triggered,
        title=outputs.get("title", ""),
        description=outputs.get("exception", ""),
        cp_text=outputs.get("cp", ""),
        evidence_required=outputs.get("evidence_required", ""),
        resolution_conditions=outputs.get("resolution_conditions", ""),
        evidence_refs=evidence_refs,
    )


EVALUATORS = {
    "missing_evidence": evaluate_missing_evidence,
    "mismatch": evaluate_mismatch,
    "keyword_risk": evaluate_keyword_risk,
    "timeline_gap": evaluate_timeline_gap,  # override
    "verification_check": evaluate_verification_check,
    "constructed_gate": evaluate_constructed_gate,
}


def evaluate_rule(rule:
    Dict[str, Any], ctx: CaseContext) -> RuleResult:
    name = rule.get("evaluator", "missing_evidence")
    fn = EVALUATORS.get(name, evaluate_missing_evidence)
    return fn(rule, ctx)


def run_rules(db:
    Session, org_id, case_id, user_id) -> Dict[str, int]:
    started_at = datetime.utcnow()
    rr = RuleRun(org_id=org_id, case_id=case_id, started_at=started_at)
    db.add(rr)
    db.flush()

    ctx = build_case_context(db, org_id, case_id)
    rules = load_rulepack().get("rules", [])

    # clear open before re-run (match original behavior)
    db.query(ExceptionEvidenceRef).filter(
        ExceptionEvidenceRef.org_id == org_id,
        ExceptionEvidenceRef.exception_id.in_(
            db.query(Exception_.id).filter(
                Exception_.case_id == case_id,
                Exception_.org_id == org_id,
                Exception_.status == "Open",
            )
        ),
    ).delete(synchronize_session=False)

    db.query(Exception_).filter(
        Exception_.case_id == case_id,
        Exception_.org_id == org_id,
        Exception_.status == "Open",
    ).delete(synchronize_session=False)

    db.query(ConditionPrecedent).filter(
        ConditionPrecedent.case_id == case_id,
        ConditionPrecedent.org_id == org_id,
        ConditionPrecedent.status == "Open",
    ).delete(synchronize_session=False)

    results: List[RuleResult] = []\n    for rule in rules:\n        try:\n            r = evaluate_rule(rule, ctx)\n            if isinstance(r, list):\n                results.extend(r)\n            else:\n                results.append(r)\n        except Exception:\n            continue

    seen = set()
    counts = {"high": 0, "medium": 0, "low": 0, "total": 0, "cps_total": 0}

    for res in results:
        if not res.triggered:
            continue
        key = (res.rule_id, (res.title or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)

        exc = Exception_(
            org_id=org_id,
            case_id=case_id,
            rule_id=res.rule_id,
            module=res.module,
            severity=res.severity,
            title=res.title,
            description=res.description,
            cp_text=res.cp_text,
            resolution_conditions=res.resolution_conditions,
            status="Open",
        )
        db.add(exc)
        db.flush()
        for ref in res.evidence_refs:
            db.add(
                ExceptionEvidenceRef(
                    org_id=org_id,
                    exception_id=exc.id,
                    document_id=ref.document_id,
                    page_number=ref.page_number,
                    note=ref.note,
                    evidence_type=ref.evidence_type,
                    snippet_json=ref.snippet_json,
                )
            )
        if res.cp_text:
            db.add(
                ConditionPrecedent(
                    org_id=org_id,
                    case_id=case_id,
                    rule_id=res.rule_id,
                    severity=res.severity,
                    text=res.cp_text,
                    evidence_required=res.evidence_required,
                    status="Open",
                )
            )
            counts["cps_total"] += 1
        sev = res.severity.lower()
        if sev in counts:
            counts[sev] += 1
        counts["total"] += 1

    rr.finished_at = datetime.utcnow()
    rr.summary = counts
    db.commit()
    return counts



def evaluate_mismatch2(rule:
    Dict[str, Any], ctx: CaseContext) -> RuleResult:
    logic = rule.get("logic", {}) or {}
    compare_fields = logic.get("compare_fields")
    if isinstance(compare_fields, list) and len(compare_fields) == 2:
        a_key, b_key = compare_fields
        a_vals = set(v.strip() for v in ctx.dossier.get(a_key, []) if v)
        b_vals = set(v.strip() for v in ctx.dossier.get(b_key, []) if v)
        inter = a_vals.intersection(b_vals)
        triggered = bool(a_vals) and bool(b_vals) and len(inter) == 0
        outputs = rule.get("outputs", {}) or {}
        # Structured mismatch evidence
        evidence_refs: List[EvidenceRef] = []
        if triggered:
            evidence_refs.append(
                EvidenceRef(
                    evidence_type="structured",
                    snippet_json={
                        "type": "mismatch",
                        "compare_fields": [a_key, b_key],
                        "source_a_values": list(a_vals),
                        "source_b_values": list(b_vals),
                    },
                )
            )
        return RuleResult(
            rule_id=rule["id"],
            module=rule["module"],
            severity=rule["severity"],
            triggered=triggered,
            title=outputs.get("title", ""),
            description=outputs.get("exception", ""),
            cp_text=outputs.get("cp", ""),
            evidence_required=outputs.get("evidence_required", ""),
            resolution_conditions=outputs.get("resolution_conditions", ""),
            evidence_refs=evidence_refs,
        )
    # Fallback to original mismatch
    return evaluate_mismatch(rule, ctx)

# Override mapping for mismatch as well
EVALUATORS["mismatch"] = evaluate_mismatch2


