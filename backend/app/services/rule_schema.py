from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml

ALLOWED_EVALUATORS = {
    "missing_evidence",
    "mismatch",
    "keyword_risk",
    "verification_check",
    "constructed_gate",
    "area_mismatch",
    "stale_document",
    "name_variation",
    "historical_keyword",
}
SEVERITIES = {"Low", "Medium", "High"}


@dataclass
class ValidationResult:
    ok: bool
    rules: List[Dict[str, Any]]
    errors: List[str]


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _validate_missing_evidence(rule_id: str, logic: Dict[str, Any]) -> Optional[str]:
    required_doc_types = _list_of_strings(logic.get("required_doc_types"))
    if not required_doc_types:
        return f"{rule_id}: missing_evidence requires non-empty logic.required_doc_types"
    return None


def _validate_mismatch(rule_id: str, logic: Dict[str, Any]) -> Optional[str]:
    field_pattern = str(logic.get("field_pattern", "")).strip()
    compare_fields = _list_of_strings(logic.get("compare_fields"))
    has_field_pattern = bool(field_pattern)
    has_compare_fields = bool(compare_fields)

    if not has_field_pattern and not has_compare_fields:
        return f"{rule_id}: mismatch requires at least one compare mode: field_pattern or compare_fields"

    if logic.get("compare_dates") and not str(logic.get("field_pattern_date", "")).strip():
        return f"{rule_id}: mismatch compare_dates requires logic.field_pattern_date"

    threshold_percent = logic.get("threshold_percent")
    if threshold_percent is not None:
        if not has_compare_fields or len(compare_fields) != 2:
            return f"{rule_id}: mismatch threshold_percent requires exactly two logic.compare_fields"
        try:
            float(threshold_percent)
        except (TypeError, ValueError):
            return f"{rule_id}: mismatch threshold_percent must be numeric"

    return None


def _validate_keyword_risk(rule_id: str, logic: Dict[str, Any], inputs: Dict[str, Any]) -> Optional[str]:
    keywords = _list_of_strings(logic.get("keywords_any")) or _list_of_strings(inputs.get("keywords"))
    if not keywords:
        return f"{rule_id}: keyword_risk requires logic.keywords_any or inputs.keywords"
    return None


def _validate_verification_check(rule_id: str, inputs: Dict[str, Any]) -> Optional[str]:
    verification_type = str(inputs.get("verification_type", "")).strip()
    keywords = _list_of_strings(inputs.get("keywords"))
    dossier_keys = _list_of_strings(inputs.get("dossier_keys"))
    if not verification_type:
        return f"{rule_id}: verification_check requires inputs.verification_type"
    if not keywords and not dossier_keys:
        return f"{rule_id}: verification_check requires inputs.keywords or inputs.dossier_keys"
    return None


def _validate_constructed_gate(rule_id: str, logic: Dict[str, Any]) -> Optional[str]:
    required_doc_types = _list_of_strings(logic.get("required_doc_types"))
    indicators = _list_of_strings(logic.get("constructed_indicators"))
    if not required_doc_types:
        return f"{rule_id}: constructed_gate requires non-empty logic.required_doc_types"
    if not indicators:
        return f"{rule_id}: constructed_gate requires non-empty logic.constructed_indicators"
    return None


def _validate_evaluator(rule_id: str, evaluator: str, logic: Dict[str, Any], inputs: Dict[str, Any]) -> Optional[str]:
    if evaluator == "timeline_gap":
        return f"{rule_id}: timeline_gap is not supported; remove it from the rulepack"
    if evaluator not in ALLOWED_EVALUATORS:
        return f"{rule_id}: unknown evaluator '{evaluator}'"
    if evaluator == "missing_evidence":
        return _validate_missing_evidence(rule_id, logic)
    if evaluator == "mismatch":
        return _validate_mismatch(rule_id, logic)
    if evaluator == "keyword_risk":
        return _validate_keyword_risk(rule_id, logic, inputs)
    if evaluator == "verification_check":
        return _validate_verification_check(rule_id, inputs)
    if evaluator == "constructed_gate":
        return _validate_constructed_gate(rule_id, logic)
    if evaluator in {"area_mismatch", "stale_document", "name_variation", "historical_keyword"}:
        return None
    return None


def _normalize_rule(rule: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        rule_id = rule.get("id")
        module = rule.get("module")
        severity = rule.get("severity")
        evaluator = rule.get("evaluator", "missing_evidence")
        outputs = dict(rule.get("outputs", {}) or {})
        logic = dict(rule.get("logic", {}) or {})
        inputs = dict(rule.get("inputs", {}) or {})

        if not rule_id or not isinstance(rule_id, str):
            return None, "rule missing id"
        if not module or not isinstance(module, str):
            return None, f"{rule_id}: missing module"
        if severity not in SEVERITIES:
            return None, f"{rule_id}: invalid severity"

        validation_error = _validate_evaluator(rule_id, str(evaluator), logic, inputs)
        if validation_error:
            return None, validation_error

        outputs.setdefault("title", "")
        outputs.setdefault("exception", "")
        outputs.setdefault("cp", "")
        outputs.setdefault("evidence_required", "")
        outputs.setdefault("resolution_conditions", "")

        normalized = {
            "id": rule_id,
            "module": module,
            "severity": severity,
            "description": rule.get("description", ""),
            "evaluator": str(evaluator),
            "is_hard_stop": bool(rule.get("is_hard_stop", False)),
            "risk_group": rule.get("risk_group"),
            "applies_when": dict(rule.get("applies_when", {}) or {}),
            "blocking_default": (
                bool(rule.get("blocking_default"))
                if rule.get("blocking_default") is not None
                else None
            ),
            "inputs": inputs,
            "logic": logic,
            "outputs": outputs,
        }
        return normalized, None
    except Exception as exc:
        return None, str(exc)


def validate_rulepack_yaml(yaml_dict: Dict[str, Any]) -> ValidationResult:
    rules_in = (yaml_dict or {}).get("rules", [])
    if not isinstance(rules_in, list):
        return ValidationResult(ok=False, rules=[], errors=["rulepack root 'rules' must be a list"])

    rules_out: List[Dict[str, Any]] = []
    errors: List[str] = []
    for rule in rules_in:
        normalized, error = _normalize_rule(rule)
        if normalized is not None:
            rules_out.append(normalized)
        else:
            errors.append(error or "unknown error")
    return ValidationResult(ok=len(errors) == 0, rules=rules_out, errors=errors)


def normalize_evidence_entry(rule_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
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


def load_evidence_library(yaml_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    rules_map = yaml_dict.get("rules") or yaml_dict.get("by_rule")
    if isinstance(rules_map, dict):
        for rule_id, entry in rules_map.items():
            out[rule_id] = normalize_evidence_entry(rule_id, entry or {})

    legacy = yaml_dict.get("evidence_options")
    if isinstance(legacy, dict):
        for rule_id, entry in legacy.items():
            out[rule_id] = normalize_evidence_entry(rule_id, entry or {})
    return out


def load_rulepack_from_path(path: str) -> ValidationResult:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return validate_rulepack_yaml(data)


def load_evidence_library_from_path(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return load_evidence_library(data)
