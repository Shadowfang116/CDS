"""Ranked next-action copy for inbox and the matter strip."""
from __future__ import annotations

from typing import Any


def rank_next_action(
    *,
    open_hard_stop_title: str | None = None,
    missing_required_causing_high: str | None = None,
    unconfirmed_key_field: str | None = None,
    open_high_title: str | None = None,
    blocking_cp_text: str | None = None,
    pending_verification: str | None = None,
    open_medium_title: str | None = None,
    open_low_title: str | None = None,
    pack_hint: str | None = None,
) -> str:
    if open_hard_stop_title:
        return f"Clear hard-stop: {open_hard_stop_title}"
    if missing_required_causing_high:
        return f"Attach required evidence: {missing_required_causing_high}"
    if unconfirmed_key_field:
        return f"Confirm {unconfirmed_key_field}"
    if open_high_title:
        return f"Review high exception: {open_high_title}"
    if blocking_cp_text:
        return f"Clear CP: {blocking_cp_text}"
    if pending_verification:
        return f"Complete verification: {pending_verification}"
    if open_medium_title:
        return f"Review exception: {open_medium_title}"
    if open_low_title:
        return f"Review exception: {open_low_title}"
    return pack_hint or "Submit for approval"


def next_action_from_aggregates(row: dict[str, Any]) -> str:
    return rank_next_action(
        open_hard_stop_title=row.get("hard_stop_title"),
        missing_required_causing_high=row.get("missing_required_label") if row.get("open_high") else None,
        unconfirmed_key_field=row.get("unconfirmed_key_field"),
        open_high_title=row.get("high_title"),
        blocking_cp_text=row.get("cp_text"),
        pending_verification=row.get("pending_verification_type"),
        open_medium_title=row.get("medium_title"),
        open_low_title=row.get("low_title"),
        pack_hint="Issue bank pack" if row.get("status") == "Approved" else "Submit for approval",
    )
