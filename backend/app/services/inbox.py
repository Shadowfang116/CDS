"""Inbox queue: one list contract for the workbench home."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.document import CaseDossierField
from app.models.rules import ConditionPrecedent, Exception_
from app.models.user import User
from app.models.verification import Verification
from app.services.next_action import next_action_from_aggregates
from app.services.rule_engine import compute_case_decision
from app.services.workflow import normalize_case_status

InboxQueue = Literal["mine", "blocked", "waiting", "ready", "aging", "all"]

TERMINAL = {"Approved", "Rejected", "Closed"}
AGING_DAYS = 3
KEY_FIELDS = (
    "party.name.borrower",
    "party.cnic",
    "property.plot_no",
    "property.plot_number",
    "property.khasra_numbers",
)


def _truncate(value: str | None, limit: int = 72) -> str | None:
    if not value:
        return None
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _first_title(rows: list[tuple[uuid.UUID, str]]) -> dict[uuid.UUID, str]:
    first: dict[uuid.UUID, str] = {}
    for case_id, title in rows:
        first.setdefault(case_id, title)
    return first


def list_inbox(
    db: Session,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    queue: InboxQueue = "all",
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    cases_q = db.query(Case).filter(Case.org_id == org_id)
    if q and q.strip():
        cases_q = cases_q.filter(Case.title.ilike(f"%{q.strip()}%"))
    cases = cases_q.order_by(Case.updated_at.desc()).all()
    case_ids = [case.id for case in cases]

    exceptions_by_case: dict[uuid.UUID, list[Exception_]] = defaultdict(list)
    if case_ids:
        for exc in db.query(Exception_).filter(Exception_.org_id == org_id, Exception_.case_id.in_(case_ids)).all():
            exceptions_by_case[exc.case_id].append(exc)

    cp_by_case: dict[uuid.UUID, list[ConditionPrecedent]] = defaultdict(list)
    if case_ids:
        for cp in (
            db.query(ConditionPrecedent)
            .filter(ConditionPrecedent.org_id == org_id, ConditionPrecedent.case_id.in_(case_ids))
            .all()
        ):
            cp_by_case[cp.case_id].append(cp)

    verif_counts = dict(
        db.query(Verification.case_id, func.count(Verification.id))
        .filter(Verification.org_id == org_id, Verification.status == "Pending")
        .group_by(Verification.case_id)
        .all()
    ) if case_ids else {}

    unconfirmed_map: dict[uuid.UUID, str] = {}
    if case_ids:
        for case_id, field_key in (
            db.query(CaseDossierField.case_id, CaseDossierField.field_key)
            .filter(
                CaseDossierField.org_id == org_id,
                CaseDossierField.case_id.in_(case_ids),
                CaseDossierField.needs_confirmation.is_(True),
                CaseDossierField.field_key.in_(KEY_FIELDS),
            )
            .all()
        ):
            unconfirmed_map.setdefault(case_id, field_key)

    assigned_ids = [case.assigned_to_user_id for case in cases if case.assigned_to_user_id]
    user_emails = {
        row.id: row.email for row in db.query(User).filter(User.id.in_(assigned_ids)).all()
    } if assigned_ids else {}

    aging_cutoff = datetime.utcnow() - timedelta(days=AGING_DAYS)
    built = []
    for case in cases:
        exceptions = exceptions_by_case.get(case.id, [])
        cps = cp_by_case.get(case.id, [])
        open_excs = [item for item in exceptions if item.status == "Open"]
        open_high_items = [item for item in open_excs if item.severity == "High"]
        open_medium_items = [item for item in open_excs if item.severity == "Medium"]
        open_low_items = [item for item in open_excs if item.severity == "Low"]
        hard_items = [item for item in open_excs if item.is_hard_stop]
        open_cps = [item for item in cps if item.status == "Open"]
        live_decision = compute_case_decision(
            exceptions,
            open_material_cps=len(open_cps),
            approval_rejected=normalize_case_status(case.status) == "Rejected",
        )
        next_action = next_action_from_aggregates(
            {
                "status": case.status,
                "hard_stop_title": _truncate(hard_items[0].title if hard_items else None),
                "open_high": len(open_high_items),
                "high_title": _truncate(open_high_items[0].title if open_high_items else None),
                "cp_text": _truncate(open_cps[0].text if open_cps else None),
                "unconfirmed_key_field": unconfirmed_map.get(case.id),
                "pending_verification_type": "mandatory check" if verif_counts.get(case.id) else None,
                "medium_title": _truncate(open_medium_items[0].title if open_medium_items else None),
                "low_title": _truncate(open_low_items[0].title if open_low_items else None),
            }
        )
        status = normalize_case_status(case.status)
        flags = {
            "mine": case.assigned_to_user_id == user_id and status not in TERMINAL,
            "blocked": live_decision == "FAIL" or bool(hard_items) or bool(open_high_items),
            "waiting": status in {"PendingDocs", "Pending Docs"},
            "ready": status in {"ReadyForApproval", "Ready for Approval"},
            "aging": bool(case.updated_at and case.updated_at <= aging_cutoff and status not in TERMINAL),
        }
        built.append(
            {
                "id": str(case.id),
                "title": case.title,
                "status": case.status,
                "decision": live_decision,
                "assigned_to_user_id": str(case.assigned_to_user_id) if case.assigned_to_user_id else None,
                "assigned_to_email": user_emails.get(case.assigned_to_user_id) if case.assigned_to_user_id else None,
                "updated_at": case.updated_at,
                "created_at": case.created_at,
                "open_high": len(open_high_items),
                "open_medium": len(open_medium_items),
                "open_low": len(open_low_items),
                "open_cps": len(open_cps),
                "open_hard_stop": len(hard_items),
                "next_action": next_action,
                "queues": [name for name, on in flags.items() if on],
            }
        )

    counts = {
        "mine": sum(1 for item in built if "mine" in item["queues"]),
        "blocked": sum(1 for item in built if "blocked" in item["queues"]),
        "waiting": sum(1 for item in built if "waiting" in item["queues"]),
        "ready": sum(1 for item in built if "ready" in item["queues"]),
        "aging": sum(1 for item in built if "aging" in item["queues"]),
        "all": len(built),
    }
    filtered = built if queue == "all" else [item for item in built if queue in item["queues"]]
    start = (page - 1) * page_size
    return {
        "items": filtered[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(filtered),
        "counts": counts,
    }
