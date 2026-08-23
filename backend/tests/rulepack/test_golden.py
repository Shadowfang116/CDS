from __future__ import annotations

import pytest

from app.services.rule_engine import (
    RuleEnginePreconditionError,
    compute_case_decision,
    evaluate_ruleset,
)
from app.services.rule_schema import load_rulepack_from_path
from rulepack.factory import RULEPACK_PATH, load_all_fixtures, make_context_from_fixture

FIXTURES = load_all_fixtures()
RULEPACK = load_rulepack_from_path(str(RULEPACK_PATH))
RULE_IDS = [rule["id"] for rule in RULEPACK.rules]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[fixture["name"] for fixture in FIXTURES])
def test_golden_fixture(fixture: dict) -> None:
    ctx = make_context_from_fixture(fixture)

    if fixture.get("expect_error"):
        with pytest.raises(RuleEnginePreconditionError, match=fixture["expect_error"]):
            evaluate_ruleset(ctx, rules=RULEPACK.rules)
        return

    results = evaluate_ruleset(ctx, rules=RULEPACK.rules)
    actual_triggered = {result.rule_id for result in results if result.triggered}
    expected_triggered = set(fixture.get("expect_triggered", []))

    assert actual_triggered == expected_triggered
    for rule_id in fixture.get("expect_not_triggered", []):
        assert rule_id not in actual_triggered

    expected_decision = fixture.get("expected_decision")
    if expected_decision:
        assert compute_case_decision(results) == expected_decision

    for rule_id in fixture.get("expect_evidence_for", []):
        result = next(item for item in results if item.rule_id == rule_id)
        assert result.triggered is True
        assert result.evidence_refs


def test_every_rule_has_fixtures() -> None:
    positive_map = {rule_id: 0 for rule_id in RULE_IDS}
    negative_map = {rule_id: 0 for rule_id in RULE_IDS}

    for fixture in FIXTURES:
        for rule_id in fixture.get("expect_triggered", []):
            positive_map[rule_id] += 1
        for rule_id in fixture.get("expect_not_triggered", []):
            negative_map[rule_id] += 1

    uncovered_positive = [rule_id for rule_id, count in positive_map.items() if count < 1]
    uncovered_negative = [rule_id for rule_id, count in negative_map.items() if count < 1]

    assert not uncovered_positive
    assert not uncovered_negative
