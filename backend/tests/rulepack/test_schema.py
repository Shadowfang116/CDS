from __future__ import annotations

import yaml

from app.services.rule_schema import validate_rulepack_yaml
from rulepack.factory import RULEPACK_PATH


def test_rulepack_schema_valid() -> None:
    parsed = yaml.safe_load(RULEPACK_PATH.read_text(encoding="utf-8"))
    result = validate_rulepack_yaml(parsed)
    assert result.ok, result.errors


def test_unknown_evaluator_is_rejected() -> None:
    result = validate_rulepack_yaml(
        {
            "rules": [
                {
                    "id": "BAD-001",
                    "module": "Test",
                    "severity": "High",
                    "evaluator": "typo_eval",
                    "logic": {"required_doc_types": ["x"]},
                    "outputs": {},
                }
            ]
        }
    )
    assert result.ok is False
    assert any("unknown evaluator" in error for error in result.errors)


def test_missing_evidence_requires_doc_types() -> None:
    result = validate_rulepack_yaml(
        {
            "rules": [
                {
                    "id": "BAD-002",
                    "module": "Test",
                    "severity": "High",
                    "evaluator": "missing_evidence",
                    "logic": {},
                    "outputs": {},
                }
            ]
        }
    )
    assert result.ok is False
    assert any("required_doc_types" in error for error in result.errors)


def test_mismatch_requires_supported_compare_mode() -> None:
    result = validate_rulepack_yaml(
        {
            "rules": [
                {
                    "id": "BAD-003",
                    "module": "Test",
                    "severity": "High",
                    "evaluator": "mismatch",
                    "logic": {"threshold_percent": 15},
                    "outputs": {},
                }
            ]
        }
    )
    assert result.ok is False
    assert any("mismatch" in error for error in result.errors)


def test_constructed_gate_requires_indicators() -> None:
    result = validate_rulepack_yaml(
        {
            "rules": [
                {
                    "id": "BAD-004",
                    "module": "Test",
                    "severity": "Medium",
                    "evaluator": "constructed_gate",
                    "logic": {"required_doc_types": ["approved_map"]},
                    "outputs": {},
                }
            ]
        }
    )
    assert result.ok is False
    assert any("constructed_indicators" in error for error in result.errors)


def test_timeline_gap_is_rejected() -> None:
    result = validate_rulepack_yaml(
        {
            "rules": [
                {
                    "id": "BAD-005",
                    "module": "Test",
                    "severity": "Medium",
                    "evaluator": "timeline_gap",
                    "logic": {"date_keywords": ["before"]},
                    "outputs": {},
                }
            ]
        }
    )
    assert result.ok is False
    assert any("timeline_gap" in error for error in result.errors)
