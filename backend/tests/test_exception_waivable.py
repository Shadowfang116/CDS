from types import SimpleNamespace

from app.services.exception_waive import exception_is_waivable


def test_hard_stop_is_not_waivable() -> None:
    assert exception_is_waivable(SimpleNamespace(is_hard_stop=True)) is False


def test_non_hard_stop_is_waivable() -> None:
    assert exception_is_waivable(SimpleNamespace(is_hard_stop=False)) is True


def test_library_non_waivable() -> None:
    item = SimpleNamespace(is_hard_stop=False, rule_id="R1")
    assert exception_is_waivable(item, library={"R1": {"waivable": False}}) is False
