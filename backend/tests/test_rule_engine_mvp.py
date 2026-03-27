import uuid
from datetime import datetime, timedelta

from app.services.rule_engine_mvp import (
    CaseContext,
    evaluate_rule,
)


def make_ctx(**kwargs):
    org_id = uuid.uuid4()
    case_id = uuid.uuid4()
    return CaseContext(
        org_id=org_id,
        case_id=case_id,
        dossier=kwargs.get("dossier", {}),
        doc_types=kwargs.get("doc_types", []),
        doc_filenames=kwargs.get("doc_filenames", []),
        documents=kwargs.get("documents", []),
        pages=kwargs.get("pages", []),
        verifications=kwargs.get("verifications", {}),
    )


def test_missing_evidence_triggers_when_doc_missing():
    rule = {
        "id": "TEST-MISS-1",
        "module": "capacity_authority",
        "severity": "High",
        "evaluator": "missing_evidence",
        "logic": {"required_doc_types": ["Guardian Court Permission"]},
        "outputs": {"title": "X", "exception": "Y", "cp": "Z"},
    }
    ctx = make_ctx(doc_types=["CNIC Copy"])  # no guardian permission
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.evidence_refs, "missing_evidence should return absence-proof evidence"
    assert (res.evidence_refs[0].snippet_json or {}).get("type") == "absence"


def test_mismatch_cnic():
    rule = {
        "id": "TEST-MISMATCH-1",
        "module": "capacity_authority",
        "severity": "Medium",
        "evaluator": "mismatch",
        "logic": {"field_pattern": "party.cnic"},
        "outputs": {"title": "CNIC Mismatch", "exception": ""},
    }
    ctx = make_ctx(dossier={"party.cnic": ["35202-1234567-1", "3520212345672"]})
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.evidence_refs, "mismatch should include structured evidence"
    assert (res.evidence_refs[0].snippet_json or {}).get("type") == "mismatch"


def test_keyword_risk_detects():
    rule = {
        "id": "TEST-KW-1",
        "module": "encumbrance",
        "severity": "High",
        "evaluator": "keyword_risk",
        "inputs": {"keywords": ["mortgage"]},
        "outputs": {"title": "Encumbrance", "exception": ""},
    }
    # one OCR page containing mortgage
    doc_id = uuid.uuid4()
    pages = [(doc_id, 1, "This sale deed refers to an existing mortgage with XYZ Bank.")]
    ctx = make_ctx(pages=pages)
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.evidence_refs and res.evidence_refs[0].page_number == 1
    # Expect OCR structured hit summary as well
    assert any((r.snippet_json or {}).get("type") == "ocr_hits" for r in res.evidence_refs)


def test_timeline_gap_stale_revenue():
    rule = {
        "id": "TEST-TIME-1",
        "module": "title_chain",
        "severity": "Medium",
        "evaluator": "timeline_gap",
        "logic": {
            "date_field": "revenue.record_date",
            "max_age_days": 365,
            "keywords_any": ["jamabandi", "fard"],
        },
        "outputs": {"title": "Stale Revenue", "exception": ""},
    }
    # older than a year
    old_date = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
    ctx = make_ctx(dossier={"revenue.record_date": [old_date]})
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.evidence_refs, "timeline_gap should include structured evidence"
    assert any((r.snippet_json or {}).get("type") == "timeline_gap" for r in res.evidence_refs)
