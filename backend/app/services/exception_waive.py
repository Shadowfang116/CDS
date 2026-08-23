"""Waive eligibility for exceptions. Hard-stop and evidence-library flags are data, not UI."""

from __future__ import annotations

from typing import Any


def exception_is_waivable(exception_item: Any, library: dict[str, Any] | None = None) -> bool:
    if bool(getattr(exception_item, "is_hard_stop", False)):
        return False
    rule_id = getattr(exception_item, "rule_id", None)
    if not rule_id:
        return True
    if library is None:
        from app.services.export_bank_pack import _load_rule_evidence_library

        library = _load_rule_evidence_library()
    entry = library.get(str(rule_id)) or {}
    return bool(entry.get("waivable", True))
