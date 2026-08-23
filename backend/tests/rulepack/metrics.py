from __future__ import annotations

from pathlib import Path
from typing import Any


def compute_rule_metrics(
    fixtures: list[dict[str, Any]],
    actual_triggered_by_fixture: dict[str, set[str]],
    rule_ids: list[str],
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}

    for rule_id in rule_ids:
        tp = fp = fn = support = 0
        for fixture in fixtures:
            if fixture.get("expect_error"):
                continue

            expected = set(fixture.get("expect_triggered", []))
            actual = actual_triggered_by_fixture[fixture["name"]]
            expected_hit = rule_id in expected
            actual_hit = rule_id in actual

            if expected_hit:
                support += 1
            if expected_hit and actual_hit:
                tp += 1
            elif expected_hit and not actual_hit:
                fn += 1
            elif actual_hit and not expected_hit:
                fp += 1

        precision = 1.0 if tp == 0 and fp == 0 else tp / (tp + fp)
        recall = 1.0 if support == 0 else tp / support
        metrics[rule_id] = {
            "support": support,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "precision": precision,
            "recall": recall,
        }

    return metrics


def write_metrics_markdown(path: Path, metrics: dict[str, dict[str, float | int]]) -> None:
    lines = [
        "# Rule Metrics",
        "",
        "| Rule ID | Support | Precision | Recall | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule_id in sorted(metrics):
        row = metrics[rule_id]
        lines.append(
            f"| {rule_id} | {row['support']} | {row['precision']:.2f} | {row['recall']:.2f} | {row['false_positive']} | {row['false_negative']} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
