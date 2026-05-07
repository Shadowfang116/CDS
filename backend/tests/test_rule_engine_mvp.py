import uuid

from app.services.rule_engine import CaseContext, evaluate_rule


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
    ctx = make_ctx(doc_types=["CNIC Copy"])
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.rule_id == "TEST-MISS-1"
    assert res.title == "X"


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
    assert res.title == "CNIC Mismatch"


def test_keyword_risk_detects():
    rule = {
        "id": "TEST-KW-1",
        "module": "encumbrance",
        "severity": "High",
        "evaluator": "keyword_risk",
        "inputs": {"keywords": ["mortgage"]},
        "outputs": {"title": "Encumbrance", "exception": ""},
    }
    doc_id = uuid.uuid4()
    pages = [(doc_id, 1, "This sale deed refers to an existing mortgage with XYZ Bank.")]
    ctx = make_ctx(pages=pages)
    res = evaluate_rule(rule, ctx)
    assert res.triggered is True
    assert res.evidence_refs and res.evidence_refs[0].page_number == 1
    assert "mortgage" in (res.description or "").lower()


def test_verification_check_skips_verified_items():
    rule = {
        "id": "TEST-VERIFY-1",
        "module": "verification",
        "severity": "Low",
        "evaluator": "verification_check",
        "inputs": {
            "verification_type": "registry",
            "keywords": ["registry"],
            "dossier_keys": ["registry"],
        },
        "outputs": {"title": "Registry verification pending", "exception": ""},
    }
    ctx = make_ctx(
        dossier={"registry.number": ["123"]},
        verifications={"registry": "Verified"},
    )
    res = evaluate_rule(rule, ctx)
    assert res.triggered is False
    assert res.title == "Registry verification pending"
