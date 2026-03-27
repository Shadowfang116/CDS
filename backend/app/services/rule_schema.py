from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml

ALLOWED_EVALUATORS = {
    "missing_evidence",
    "mismatch",
    "keyword_risk",
    "timeline_gap",
    # kept for backward compatibility
    "verification_check",
    "constructed_gate",
}


@dataclass
class ValidationResult:
    ok: bool
    rules: List[Dict[str, Any]]
    errors: List[str]


def _normalize_rule(r:
    Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        rid = r.get("id")
        mod = r.get("module")
        sev = r.get("severity")
        ev = r.get("evaluator", "missing_evidence")
        risk_group = r.get("risk_group")  # optional canonical grouping
        blocking_default = r.get("blocking_default")  # optional boolean
        outputs = r.get("outputs", {}) or {}
        logic = r.get("logic", {}) or {}
        inputs = r.get("inputs", {}) or {}
        if not rid or not isinstance(rid, str):
            return None, "rule missing id"
        if not mod or not isinstance(mod, str):
            return None, f"{rid}: missing module"
        if not sev or sev not in {"Low", "Medium", "High"}:
            return None, f"{rid}: invalid severity"
        if ev not in ALLOWED_EVALUATORS:
            # allow unknown but map to missing_evidence to avoid crashes
            ev = "missing_evidence"
        # Ensure required output fields exist (empty strings acceptable)
        outputs.setdefault("title", "")
        outputs.setdefault("exception", "")
        outputs.setdefault("cp", "")
        outputs.setdefault("evidence_required", "")
        outputs.setdefault("resolution_conditions", "")
        nr = {
            "id": rid,
            "module": mod,
            "severity": sev,
            "evaluator": ev,
            "risk_group": risk_group,  # may be None; API will derive if missing
            "blocking_default": bool(blocking_default) if blocking_default is not None else None,
            "inputs": inputs,
            "logic": logic,
            "outputs": outputs,
        }
        return nr, None
    except Exception as e:
        return None, str(e)


def validate_rulepack_yaml(yaml_dict:
    Dict[str, Any]) -> ValidationResult:
    rules_in = (yaml_dict or {}).get("rules", [])
    rules_out: List[Dict[str, Any]] = []
    errors: List[str] = []
    for r in rules_in:
        nr, err = _normalize_rule(r)
        if nr is not None:
            rules_out.append(nr)
        else:
            errors.append(err or "unknown error")
    return ValidationResult(ok=len(errors) == 0, rules=rules_out, errors=errors)


# Evidence library normalization (backward compatible with existing keys)

def normalize_evidence_entry(rule_id:
    str, entry: Dict[str, Any]) -> Dict[str, Any]:
    # Old schema: {primary: [...], substitutes: [...], notes: str}
    # New canonical: {acceptable_evidence: [...], acceptable_substitutes: [...], closure_logic: str, waivable: bool, waiver_guidance: str, notes: str}
    acceptable = entry.get("acceptable_evidence") or entry.get("primary") or []
    substitutes = entry.get("acceptable_substitutes") or entry.get("substitutes") or []
    closure_logic = entry.get("closure_logic") or "any_of"
    waivable = bool(entry.get("waivable", True))
    waiver_guidance = entry.get("waiver_guidance") or entry.get("notes") or ""
    notes = entry.get("notes") or ""
    return {
        "rule_id": rule_id,
        "acceptable_evidence": list(acceptable),
        "acceptable_substitutes": list(substitutes),
        "closure_logic": closure_logic,
        "waivable": waivable,
        "waiver_guidance": waiver_guidance,
        "notes": notes,
    }


def load_evidence_library(yaml_dict:
    Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    # Support new structure
    rules_map = yaml_dict.get("rules") or yaml_dict.get("by_rule")
    if isinstance(rules_map, dict):
        for rid, entry in rules_map.items():
            out[rid] = normalize_evidence_entry(rid, entry or {})
    # Support existing `evidence_options` structure
    legacy = yaml_dict.get("evidence_options")
    if isinstance(legacy, dict):
        for rid, entry in legacy.items():
            out[rid] = normalize_evidence_entry(rid, entry or {})
    return out


def load_rulepack_from_path(path:
    str) -> ValidationResult:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return validate_rulepack_yaml(data)


def load_evidence_library_from_path(path:
    str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return load_evidence_library(data)

