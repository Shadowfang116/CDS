from __future__ import annotations

from app.services.rule_engine import evaluate_ruleset
from app.services.rule_schema import load_rulepack_from_path
from rulepack.factory import METRICS_PATH, RULEPACK_PATH, load_all_fixtures, make_context_from_fixture
from rulepack.metrics import compute_rule_metrics, write_metrics_markdown


def test_rule_metrics_are_locked_to_one() -> None:
    fixtures = [fixture for fixture in load_all_fixtures() if not fixture.get("expect_error")]
    rulepack = load_rulepack_from_path(str(RULEPACK_PATH))
    actual_triggered_by_fixture: dict[str, set[str]] = {}

    for fixture in fixtures:
        ctx = make_context_from_fixture(fixture)
        results = evaluate_ruleset(ctx, rules=rulepack.rules)
        actual_triggered_by_fixture[fixture["name"]] = {
            result.rule_id for result in results if result.triggered
        }

    metrics = compute_rule_metrics(
        fixtures=fixtures,
        actual_triggered_by_fixture=actual_triggered_by_fixture,
        rule_ids=[rule["id"] for rule in rulepack.rules],
    )
    write_metrics_markdown(METRICS_PATH, metrics)

    for rule_id, row in metrics.items():
        assert row["precision"] >= 1.0, rule_id
        assert row["recall"] >= 1.0, rule_id
