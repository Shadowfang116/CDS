from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from app.models.case import Case


def empty_dossier() -> dict[str, Any]:
    return {
        "version": 1,
        "fields": {},
        "revision_history": [],
    }


def ensure_case_dossier(case: Case) -> dict[str, Any]:
    dossier = deepcopy(case.dossier_json or empty_dossier())
    dossier.setdefault("version", 1)
    dossier.setdefault("fields", {})
    dossier.setdefault("revision_history", [])
    return dossier


def save_case_dossier_revision(
    case: Case,
    *,
    actor_id: str,
    summary: str,
    field_key: str | None = None,
    before_value: Any = None,
    after_value: Any = None,
) -> dict[str, Any]:
    dossier = ensure_case_dossier(case)
    dossier["version"] = int(dossier.get("version", 1)) + 1
    dossier["revision_history"].append(
        {
            "version": dossier["version"],
            "timestamp": datetime.utcnow().isoformat(),
            "actor_id": actor_id,
            "summary": summary,
            "field_key": field_key,
            "before_value": before_value,
            "after_value": after_value,
        }
    )
    case.dossier_json = dossier
    return dossier


def upsert_dossier_field(
    case: Case,
    *,
    key: str,
    value: Any,
    source: str,
    locked: bool,
    actor_id: str,
    summary: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    dossier = ensure_case_dossier(case)
    current = dossier["fields"].get(key)
    if current and current.get("locked") and source != "manual":
        case.dossier_json = dossier
        return dossier, current

    dossier["fields"][key] = {
        "value": value,
        "source": source,
        "locked": locked,
    }
    case.dossier_json = dossier
    save_case_dossier_revision(
        case,
        actor_id=actor_id,
        summary=summary,
        field_key=key,
        before_value=current.get("value") if current else None,
        after_value=value,
    )
    return ensure_case_dossier(case), current
