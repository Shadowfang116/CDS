from __future__ import annotations

from types import SimpleNamespace

from app.services.rule_engine import compute_case_decision


def _item(*, severity: str, is_hard_stop: bool = False, status: str = "Open", triggered: bool = True):
    return SimpleNamespace(
        severity=severity,
        is_hard_stop=is_hard_stop,
        status=status,
        triggered=triggered,
    )


def test_compute_case_decision_pass() -> None:
    assert compute_case_decision([_item(severity="Medium"), _item(severity="Low")]) == "PASS"


def test_compute_case_decision_fail_for_open_high() -> None:
    assert compute_case_decision([_item(severity="High")]) == "FAIL"


def test_compute_case_decision_fail_for_hard_stop() -> None:
    assert compute_case_decision([_item(severity="High", is_hard_stop=True)]) == "FAIL"


def test_compute_case_decision_conditional_pass_for_waived_high() -> None:
    assert compute_case_decision([_item(severity="High", status="Waived")]) == "CONDITIONAL_PASS"


def test_compute_case_decision_conditional_pass_for_open_cps() -> None:
    assert (
        compute_case_decision(
            [_item(severity="Medium")],
            open_material_cps=1,
        )
        == "CONDITIONAL_PASS"
    )


def test_compute_case_decision_fail_for_rejected_approval() -> None:
    assert compute_case_decision([], approval_rejected=True) == "FAIL"


def test_compute_case_decision_conditional_when_fields_unconfirmed() -> None:
    assert (
        compute_case_decision(
            [_item(severity="Low")],
            required_fields_confirmed=False,
        )
        == "CONDITIONAL_PASS"
    )
