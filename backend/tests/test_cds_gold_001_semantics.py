"""CDS-GOLD-001 semantic regressions: arbitration, classification, gold rules."""
import uuid

from app.services.canonical_docs import classify_document_type, canonical_key
from app.services.extractors.candidate_arbitration import (
    CandidateSnapshot,
    arbitrate_candidate,
)
from app.services.extractors.document_facts import area_to_marlas, extract_document_facts
from app.services.rule_engine import CaseContext, evaluate_rule


def _snap(**kwargs):
    defaults = {
        "id": None,
        "document_id": "doc-a",
        "field_key": "party.seller.names",
        "value": "محمد اکرم",
        "confidence": 0.95,
        "method": "clause_urdu",
        "status": "Pending",
    }
    defaults.update(kwargs)
    return CandidateSnapshot(**defaults)


def test_sale_deed_clause_survives_later_mutation_candidate():
    existing = [_snap(id="c1", document_id="sale-deed")]
    incoming = _snap(
        document_id="mutation",
        value="رجسٹریشن حوالہ",
        confidence=0.85,
        method="labelled",
    )
    decision = arbitrate_candidate(existing, incoming)
    assert decision.action == "keep_conflict"
    assert decision.mark_review is True


def test_weaker_same_source_does_not_downgrade():
    existing = [_snap(id="c1", document_id="sale-deed", method="clause_urdu", confidence=0.95)]
    incoming = _snap(
        document_id="sale-deed",
        value="فروخت کنندہ",
        confidence=0.40,
        method="anchor",
    )
    decision = arbitrate_candidate(existing, incoming)
    assert decision.action == "skip_downgrade"
    assert decision.target_id == "c1"


def test_canonical_types_for_gold_corpus_filenames():
    cases = {
        "01_Registered_Sale_Deed_URDU.pdf": "Sale Deed",
        "02_Mutation_Intiqal_URDU.pdf": "Mutation",
        "03_Fard_URDU.pdf": "Fard",
        "04_Society_NOC_URDU.pdf": "Society/Authority NOC",
        "07_Search_Report_URDU.pdf": "Search Report",
        "09_Possession_Letter_URDU.pdf": "Possession Letter",
        "10_Property_Tax_PT10_Clearance_URDU.pdf": "Property Tax/PT-10",
        "11_Board_Resolution_URDU.pdf": "Board Resolution",
        "12_Approved_Building_Plan_URDU.pdf": "Building Plan",
        "14_Development_Charges_Clearance_URDU.pdf": "Dues Clearance",
        "15_Prior_Charge_Release_Letter_URDU.pdf": "Charge Release",
        "16_Identity_Name_Confirmation_URDU.pdf": "Identity Confirmation",
    }
    for filename, expected in cases.items():
        classified, _source = classify_document_type(filename, "")
        assert classified == expected, filename
    assert canonical_key("Sale Deed") == canonical_key("registry_deed")
    assert canonical_key("Possession Letter") == canonical_key("possession_affidavit")


def test_area_fact_parses_kanal_marla():
    text = "رقبہ 3 کانال 18 مرلہ"
    facts = extract_document_facts(text=text, page_number=1, filename="03_Fard_URDU.pdf", doc_type="Fard")
    areas = [fact for fact in facts if fact.key == "fact.area"]
    assert areas
    assert area_to_marlas(areas[0].value) == 78.0
    assert area_to_marlas("4 Kanal") == 80.0


def test_company_mortgage_skips_photograph_rule():
    rule = {
        "id": "KYC-02",
        "module": "Identity/KYC",
        "severity": "High",
        "evaluator": "missing_evidence",
        "applies_when": {"borrower_type": ["individual"]},
        "logic": {"required_doc_types": ["Photograph"]},
        "outputs": {"title": "Missing Borrower Photograph", "exception": "x"},
    }
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Sale Deed"],
        doc_filenames=[],
        documents=[],
        pages=[],
        borrower_type="company",
        transaction_type="mortgage",
    )
    from app.services.rule_engine import _rule_applies
    assert _rule_applies(ctx, rule) is False


def test_gold_area_mismatch_evaluator():
    from app.services.extractors.document_facts import DocumentFact

    rule = {
        "id": "GOLD-AREA-01",
        "module": "Title/Area",
        "severity": "High",
        "evaluator": "area_mismatch",
        "logic": {},
        "outputs": {"title": "Property area mismatch", "exception": "mismatch"},
    }
    sale_id = uuid.uuid4()
    fard_id = uuid.uuid4()
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Sale Deed", "Fard"],
        doc_filenames=[],
        documents=[],
        pages=[],
        document_facts=[
            DocumentFact("fact.area", "4 Kanal", 1, "", doc_type="Sale Deed", document_id=str(sale_id)),
            DocumentFact("fact.area", "3 Kanal 18 Marla", 1, "", doc_type="Fard", document_id=str(fard_id)),
        ],
    )
    result = evaluate_rule(rule, ctx)
    assert result.triggered is True
    ctx_resolved = CaseContext(
        org_id=ctx.org_id,
        case_id=ctx.case_id,
        dossier={},
        doc_types=["Sale Deed", "Fard"],
        doc_filenames=[],
        documents=[],
        pages=[],
        document_facts=[
            DocumentFact("fact.area", "4 Kanal", 1, "", doc_type="Sale Deed", document_id=str(sale_id)),
            DocumentFact("fact.area", "4 Kanal", 1, "", doc_type="Fard", document_id=str(fard_id)),
        ],
    )
    assert evaluate_rule(rule, ctx_resolved).triggered is False


def test_filename_wins_over_mutation_content():
    mutationish = "انتقال منتقل کنندہ منتقل الیہ mutation intiqal"
    cases = {
        "03_Fard_Old_URDU.pdf": "Fard",
        "06_Title_Search_Report_URDU.pdf": "Search Report",
        "07_Valuation_Report_URDU.pdf": "Valuation",
        "08_Facility_Approval_URDU.pdf": "Facility Approval",
        "10_Property_Tax_PT10_Clearance_URDU.pdf": "Property Tax/PT-10",
        "09_Possession_Letter_URDU.pdf": "Possession Letter",
        "01_Registered_Sale_Deed_URDU.pdf": "Sale Deed",
        "02_Mutation_Intiqal_URDU.pdf": "Mutation",
    }
    for filename, expected in cases.items():
        classified, source = classify_document_type(filename, mutationish)
        assert classified == expected, filename
        if expected != "Mutation":
            assert source == "filename"


def test_owner_fact_rejects_label_fragments():
    garbage = "مالک ملاحظہ کے لیے ان / حصص داران منتقل الیہ"
    facts = extract_document_facts(
        text=garbage,
        page_number=1,
        filename="03_Fard_URDU.pdf",
        doc_type="Fard",
    )
    owners = [fact for fact in facts if fact.key == "fact.owner_name"]
    assert owners == []

    named = "مالک: محمد اکرم ولد عبدالله"
    facts_ok = extract_document_facts(
        text=named,
        page_number=1,
        filename="03_Fard_URDU.pdf",
        doc_type="Fard",
    )
    owners_ok = [fact for fact in facts_ok if fact.key == "fact.owner_name"]
    assert owners_ok
    assert "محمد اکرم" in owners_ok[0].value


def test_name_variation_ignores_implausible_owners():
    from app.services.extractors.document_facts import DocumentFact

    rule = {
        "id": "GOLD-NAME-01",
        "module": "Identity/KYC",
        "severity": "Medium",
        "evaluator": "name_variation",
        "logic": {"cleared_by_doc_types": ["Identity Confirmation"]},
        "outputs": {"title": "Party name variation", "exception": "vary"},
    }
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Sale Deed", "Fard"],
        doc_filenames=[],
        documents=[],
        pages=[],
        document_facts=[
            DocumentFact("party.buyer.names", "اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ", 1, "", doc_type="Sale Deed"),
            DocumentFact("fact.owner_name", "ملاحظہ", 1, "", doc_type="Fard"),
        ],
    )
    assert evaluate_rule(rule, ctx).triggered is False


def test_infer_borrower_type_from_company_markers():
    from app.services.dossier_autofill import infer_borrower_type

    class _Doc:
        doc_type = "Sale Deed"
        original_filename = "01_Registered_Sale_Deed_URDU.pdf"

    assert infer_borrower_type([_Doc()], "خریدار کمپنی اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ", []) == "company"
    assert infer_borrower_type([], "فرد رقبہ", []) == "individual"


def test_area_mismatch_prefers_fard_over_matching_mutation():
    from datetime import datetime, timezone
    from app.services.extractors.document_facts import DocumentFact

    class _Doc:
        def __init__(self, doc_id, doc_type, created):
            self.id = doc_id
            self.doc_type = doc_type
            self.original_filename = f"{doc_type}.pdf"
            self.created_at = created

    rule = {
        "id": "GOLD-AREA-01",
        "module": "Title/Area",
        "severity": "High",
        "evaluator": "area_mismatch",
        "logic": {},
        "outputs": {"title": "Property area mismatch", "exception": "mismatch"},
    }
    sale_id = uuid.uuid4()
    mut_id = uuid.uuid4()
    fard_id = uuid.uuid4()
    now = datetime(2026, 8, 17, 17, 32, 58, tzinfo=timezone.utc)
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Sale Deed", "Mutation", "Fard"],
        doc_filenames=[],
        documents=[
            _Doc(sale_id, "Sale Deed", now),
            _Doc(mut_id, "Mutation", now),
            _Doc(fard_id, "Fard", now),
        ],
        pages=[],
        document_facts=[
            DocumentFact("fact.area", "4 Kanal", 2, "", doc_type="Sale Deed", document_id=str(sale_id)),
            DocumentFact("fact.area", "4 Kanal", 2, "", doc_type="Mutation", document_id=str(mut_id)),
            DocumentFact("fact.area", "3 Kanal 18 Marla", 2, "", doc_type="Fard", document_id=str(fard_id)),
        ],
    )
    assert evaluate_rule(rule, ctx).triggered is True


def test_area_mismatch_requires_title_and_revenue_sources():
    from app.services.extractors.document_facts import DocumentFact

    rule = {
        "id": "GOLD-AREA-01",
        "module": "Title/Area",
        "severity": "High",
        "evaluator": "area_mismatch",
        "logic": {},
        "outputs": {"title": "Property area mismatch", "exception": "mismatch"},
    }
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Search Report", "Valuation"],
        doc_filenames=[],
        documents=[],
        pages=[],
        document_facts=[
            DocumentFact("fact.area", "18 Marla", 1, "", doc_type="Search Report"),
            DocumentFact("fact.area", "10 Marla", 1, "", doc_type="Valuation"),
        ],
    )
    assert evaluate_rule(rule, ctx).triggered is False


def test_stale_fard_undated_newest_is_unconfirmed():
    from datetime import datetime, timezone
    from app.services.extractors.document_facts import DocumentFact

    class _Doc:
        def __init__(self, doc_id, created):
            self.id = doc_id
            self.doc_type = "Fard"
            self.original_filename = "fard.pdf"
            self.created_at = created

    rule = {
        "id": "GOLD-FARD-01",
        "module": "Title/Timeline",
        "severity": "Medium",
        "evaluator": "stale_document",
        "logic": {"doc_types": ["Fard"], "max_age_days": 90},
        "outputs": {"title": "Stale fard", "exception": "stale"},
    }
    old_id = uuid.uuid4()
    new_id = uuid.uuid4()
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Fard"],
        doc_filenames=[],
        documents=[
            _Doc(old_id, datetime(2026, 1, 20, tzinfo=timezone.utc)),
            _Doc(new_id, datetime.now(timezone.utc)),
        ],
        pages=[],
        document_facts=[
            DocumentFact("fact.issue_date", "2026-01-15", 1, "", doc_type="Fard", document_id=str(old_id)),
        ],
    )
    result = evaluate_rule(rule, ctx)
    assert result.triggered is True
    assert "unconfirmed" in result.title.lower()


def test_total_area_prefers_kul_raqba_over_khasra_and_reads_jus():
    khasra_and_total = (
        "118/2 1 کنال 10 مرلہ\n119/1 1 کنال 10 مرلہ\n"
        "کل رقبہ حسبِ اس فرد: 3 JUS 18 مرلہ۔ یہ رقبہ بیع نامہ اور انتقال میں درج 4 کنال سے مختلف ہے۔"
    )
    facts = extract_document_facts(
        text=khasra_and_total,
        page_number=2,
        filename="03_Fard_URDU.pdf",
        doc_type="Fard",
    )
    areas = [fact for fact in facts if fact.key == "fact.area"]
    assert areas
    assert area_to_marlas(areas[0].value) == 78.0

    deed = extract_document_facts(
        text="کل رقبہ 4 Jus (چار JUS) صنعتی پلاٹ",
        page_number=2,
        filename="01_Registered_Sale_Deed_URDU.pdf",
        doc_type="Sale Deed",
    )
    deed_areas = [fact for fact in deed if fact.key == "fact.area"]
    assert deed_areas
    assert area_to_marlas(deed_areas[0].value) == 80.0

    corrected = extract_document_facts(
        text="کل رقبہ: 4 JUS\nکل رقبہ 4 کنال",
        page_number=2,
        filename="13_Corrected_Fard_URDU.pdf",
        doc_type="Fard",
    )
    corrected_areas = [fact for fact in corrected if fact.key == "fact.area"]
    assert corrected_areas
    assert area_to_marlas(corrected_areas[0].value) == 80.0


def test_fard_issue_date_reads_ocr_august_alias():
    facts = extract_document_facts(
        text="فرد آئی ڈی FARD-T-2026-001184\nتاریخ اجرا 8 گست 2026\nمقصد بینک رہن",
        page_number=1,
        filename="13_Corrected_Fard_URDU.pdf",
        doc_type="Fard",
    )
    dates = [fact for fact in facts if fact.key == "fact.issue_date"]
    assert dates
    assert dates[0].value == "2026-08-08"


def test_tax_history_from_historic_receipt_language():
    text = (
        "کمپیوٹرائزڈ ریکارڈ کے مطابق مالی سال 27-2026 تک موجودہ پراپرٹی ٹیکس واجبات ادا شدہ "
        "ظاہر کیے گئے ہیں۔ تاہم 20-2019 کا تاریخی paper receipt ابتدائی فائل میں دستیاب نہیں, "
        "جسے CDS کے Waiver scenario میں استعمال کیا جا سکتا"
    )
    facts = extract_document_facts(
        text=text,
        page_number=2,
        filename="10_Property_Tax_PT10_Clearance_URDU.pdf",
        doc_type="Property Tax/PT-10",
    )
    tax = [fact for fact in facts if fact.key == "fact.tax_history"]
    assert tax


def test_stale_fard_cleared_by_newer_dated_fard():
    from datetime import datetime, timezone
    from app.services.extractors.document_facts import DocumentFact

    class _Doc:
        def __init__(self, doc_id, created):
            self.id = doc_id
            self.doc_type = "Fard"
            self.original_filename = "fard.pdf"
            self.created_at = created

    rule = {
        "id": "GOLD-FARD-01",
        "module": "Title/Timeline",
        "severity": "Medium",
        "evaluator": "stale_document",
        "logic": {"doc_types": ["Fard"], "max_age_days": 90, "as_of_date": "2026-08-17"},
        "outputs": {"title": "Stale fard", "exception": "stale"},
    }
    old_id = uuid.uuid4()
    new_id = uuid.uuid4()
    ctx = CaseContext(
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        dossier={},
        doc_types=["Fard"],
        doc_filenames=[],
        documents=[
            _Doc(old_id, datetime(2026, 6, 1, tzinfo=timezone.utc)),
            _Doc(new_id, datetime(2026, 8, 17, tzinfo=timezone.utc)),
        ],
        pages=[],
        document_facts=[
            DocumentFact("fact.issue_date", "2026-01-15", 1, "", doc_type="Fard", document_id=str(old_id)),
            DocumentFact("fact.issue_date", "2026-08-08", 1, "", doc_type="Fard", document_id=str(new_id)),
        ],
    )
    assert evaluate_rule(rule, ctx).triggered is False


