"""FindingView serializers and active Punjab rulepack invariants."""
from pathlib import Path
from types import SimpleNamespace

from app.services.workbench import finding_view_from_cp, finding_view_from_exception
from app.services.rule_schema import load_rulepack_from_path

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_PACK = REPO_ROOT / "docs" / "rulepacks" / "punjab_mortgage_v1.yaml"
ARCHIVE_PACK = REPO_ROOT / "docs" / "rulepacks" / "archive" / "generic_mvp_legacy.yaml"


def test_finding_view_from_exception_keeps_gold_fields(monkeypatch):
    monkeypatch.setattr("app.services.workbench.exception_is_waivable", lambda item, library=None: True)
    item = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        rule_id="GOLD-TAX-01",
        module="Municipal",
        severity="Low",
        status="Open",
        title="Historical property tax",
        description="Historic arrears",
        cp_text="Confirm current-year tax",
        resolution_conditions="Waive with documented reason",
        evidence_refs=[{"document_id": "doc-1", "page_number": 2}],
        is_hard_stop=False,
        waiver_reason=None,
        source_document_id=None,
        source_page=None,
    )
    view = finding_view_from_exception(item)
    assert view["kind"] == "exception"
    assert view["rule_id"] == "GOLD-TAX-01"
    assert view["waivable"] is True
    assert view["is_hard_stop"] is False
    assert view["evidence_refs"][0]["page_number"] == 2


def test_finding_view_from_cp_is_serializer_not_table():
    item = SimpleNamespace(
        id="22222222-2222-2222-2222-222222222222",
        rule_id="GOLD-PLAN-01",
        severity="High",
        status="Open",
        text="Obtain the approved building plan",
        evidence_required="Approved building plan",
        waiver_reason=None,
    )
    view = finding_view_from_cp(item)
    assert view["kind"] == "cp"
    assert view["title"] == "Obtain the approved building plan"
    assert view["status"] == "Open"


def test_active_punjab_pack_keeps_gold_drops_archived_kyc():
    pack = load_rulepack_from_path(str(ACTIVE_PACK))
    assert pack.ok, pack.errors
    ids = {rule["id"] for rule in pack.rules}
    gold = {
        "GOLD-AREA-01",
        "GOLD-PLAN-01",
        "GOLD-DUES-01",
        "GOLD-ENCUMB-01",
        "GOLD-FARD-01",
        "GOLD-NAME-01",
        "GOLD-TAX-01",
    }
    assert gold <= ids
    assert "KYC-01" in ids
    assert "KYC-02" not in ids
    assert "KYC-05" not in ids
    assert "KYC-07" not in ids
    assert "KYC-10" not in ids
    archived = load_rulepack_from_path(str(ARCHIVE_PACK))
    assert archived.ok, archived.errors
    archived_ids = {rule["id"] for rule in archived.rules}
    assert archived_ids == {"KYC-02", "KYC-05", "KYC-07", "KYC-10"}
