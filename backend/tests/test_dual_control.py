import inspect

from app.services.approvals import decide_approval_request


def test_dual_control_has_no_admin_exception() -> None:
    source = inspect.getsource(decide_approval_request)
    assert "requested_by_user_id == decided_by_user_id" in source
    assert "Dual control violation" in source
    assert "if current_user.role == \"Admin\"" not in source
    assert "role_satisfies" not in source.split("requested_by_user_id == decided_by_user_id")[1][:400]
