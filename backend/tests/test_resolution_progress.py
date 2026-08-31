from types import SimpleNamespace

from app.services.resolution import compute_reconciled_decision, lifecycle_status_after_reconcile


def test_reconciled_decision_drops_fail_after_open_high_is_resolved() -> None:
    exceptions = [
        SimpleNamespace(status="Resolved", severity="High", is_hard_stop=True, triggered=True),
    ]
    cps = [SimpleNamespace(status="Satisfied")]

    assert compute_reconciled_decision(exceptions, cps) == "PASS"


def test_reconciled_decision_is_conditional_when_open_cp_remains() -> None:
    exceptions = [
        SimpleNamespace(status="Resolved", severity="High", is_hard_stop=False, triggered=True),
    ]
    cps = [SimpleNamespace(status="Open")]

    assert compute_reconciled_decision(exceptions, cps) == "CONDITIONAL_PASS"


def test_ready_review_moves_to_ready_for_approval() -> None:
    assert lifecycle_status_after_reconcile("Review", ready=True, decision="PASS") == "Ready for Approval"


def test_new_matter_does_not_skip_processing_stage() -> None:
    assert lifecycle_status_after_reconcile("New", ready=True, decision="PASS") == "Processing"


def test_ready_matter_reopens_when_resolution_reopens_blocker() -> None:
    assert lifecycle_status_after_reconcile("Ready for Approval", ready=False, decision="FAIL") == "Review"
