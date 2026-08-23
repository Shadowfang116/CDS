"""Contextual autofill: sale-deed clauses, garbage refusal, plot/block, routing."""
from app.services.dossier_autofill import (
    apply_cross_doc_consensus,
    extract_block,
    extract_plot_number,
    party_role_confidence,
)
from app.services.extractors.candidate_gate import normalize_and_validate_candidate
from app.services.extractors.doc_routing import allows_party_roles, classify_document
from app.services.extractors.party_roles import PageOCR, extract_party_roles_from_document
from app.services.extractors.sale_deed_clauses import extract_sale_deed_clauses
from app.services.extractors.validators import is_extraction_garbage, is_plausible_party_name


SALE_DEED_RECITAL = (
    "یہ بیع نامہ آج مورخہ 12 مارچ 2021 کو لاہور میں تحریر ہوا۔ "
    "فروخت کنندہ جناب محمد اکرم ولد محمد یوسف, بالغ, پاکستانی "
    "شہری, فرضی شناختی کارڈ نمبر 0-1111111-00000, ساکن لاہور "
    "(جسے آئندہ اس دستاویز میں ''فروخت کنندہ\" کہا جائے گا) "
    "ایک جانب, اور خریدار کمپنی اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ "
    "کمپنی رجسٹریشن نمبر ۲-000000/ جس کا رجسٹرڈ دفتر "
    "لاہور میں واقع ہے, بذریعہ مجاز ڈائریکٹر جناب سلیم محمود "
    "(جسے آئندہ ''خریدار\" کہا جائے گا) دوسری جانب, باہمی رضامندی سے "
    "درج ذیل شرائط پر متفق ہوئے۔ "
    "جائیداد | پلاٹ نمبر 82 صنعتی بلاک۔بی, ماڈل انڈسٹریل اسٹیٹ, لاہور"
)

PT10_HEADER = (
    "SAMPLE - NOT A REAL DOCUMENT | حقیقی دستاویز "
    "Industrial Block-B مقامی علاقہ "
    "T-P-82/IND .Property No "
    "مالک اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ "
    "CDS-GOLD-001 | فرضی تربیتی کیس"
)

WATERMARK = "CDS-GOLD-001 | فرضی تربیتی"
BOILERPLATE_BUYER = "درج ذیل شرائط پر متفق ہوئے۔"
ROLE_BLEED_SELLER = "ایک جانب, اور خریدار کمپنی اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ"


def test_clause_parser_extracts_seller_and_buyer_not_witness():
    pages = [PageOCR("doc-1", "01_Registered_Sale_Deed_URDU.pdf", 1, SALE_DEED_RECITAL)]
    hits = extract_sale_deed_clauses(pages)
    assert "seller" in hits
    assert "محمد اکرم" in hits["seller"].value
    assert hits["seller"].char_start > 0
    assert SALE_DEED_RECITAL[hits["seller"].char_start:hits["seller"].char_end]
    assert "buyer" in hits
    assert "اے بی سی ٹیکسٹائلز" in hits["buyer"].value
    assert "لمیٹڈ" in hits["buyer"].value
    assert "witness" not in hits


def test_party_roles_prefers_clause_over_labelled_window():
    pages = [PageOCR("doc-1", "01_Registered_Sale_Deed_URDU.pdf", 1, SALE_DEED_RECITAL)]
    roles = extract_party_roles_from_document(pages)
    assert "محمد اکرم" in roles["seller_names"]
    assert "اے بی سی ٹیکسٹائلز" in roles["buyer_names"]
    assert not roles["witness_names"]
    assert roles["evidence"]["role_method"]["seller"] == "clause_urdu"
    assert roles["evidence"]["role_method"]["buyer"] == "clause_urdu"
    assert roles["evidence"]["role_spans"]["seller"]["char_start"] > 0


def test_watermark_and_boilerplate_are_garbage():
    assert is_extraction_garbage(WATERMARK, role="witness")[0] is True
    assert is_extraction_garbage(BOILERPLATE_BUYER, role="buyer")[0] is True
    assert is_extraction_garbage(ROLE_BLEED_SELLER, role="seller")[0] is True
    assert is_plausible_party_name(WATERMARK, role="witness")[0] is False
    assert is_plausible_party_name(BOILERPLATE_BUYER, role="buyer")[0] is False
    assert is_plausible_party_name("محمد اکرم", role="seller")[0] is True
    assert is_plausible_party_name("اے بی سی ٹیکسٹائلز (پرائیویٹ) لمیٹڈ", role="buyer")[0] is True


def test_candidate_gate_refuses_garbage_allows_party_semicolons():
    ok, _, reason = normalize_and_validate_candidate("party.witness.names", WATERMARK)
    assert ok is False
    assert reason
    ok, normalized, _ = normalize_and_validate_candidate(
        "party.seller.names", "محمد اکرم؛ علی خان"
    )
    assert ok is True
    assert normalized


def test_plot_and_block_from_sale_deed_and_pt10():
    plot = extract_plot_number(SALE_DEED_RECITAL)
    block = extract_block(SALE_DEED_RECITAL)
    assert plot and plot[0][0] == "82"
    assert block and block[0][0] == "B"

    pt_plot = extract_plot_number(PT10_HEADER)
    pt_block = extract_block(PT10_HEADER)
    assert pt_plot and pt_plot[0][0] == "82"
    assert pt_block and pt_block[0][0] == "B"


def test_doc_routing_sale_deed_vs_tax():
    assert classify_document("01_Registered_Sale_Deed_URDU.pdf", SALE_DEED_RECITAL) == "sale_deed"
    assert allows_party_roles("sale_deed") is True
    assert classify_document("10_Property_Tax_PT10_Clearance_URDU.pdf", PT10_HEADER) == "tax"
    assert allows_party_roles("tax") is False


def test_pt10_does_not_emit_party_roles():
    pages = [PageOCR("doc-tax", "10_Property_Tax_PT10_Clearance_URDU.pdf", 1, PT10_HEADER)]
    roles = extract_party_roles_from_document(pages)
    assert not roles["seller_names"]
    assert not roles["buyer_names"]
    assert not roles["witness_names"]


def test_plot_block_consensus_and_clause_confidence():
    all_extractions = {
        "property.plot_number": [
            ("82", 0.85, "doc-a", 1, 10, 12),
            ("82", 0.70, "doc-b", 1, 4, 6),
            ("9", 0.70, "doc-c", 1, 1, 2),
        ]
    }
    apply_cross_doc_consensus(all_extractions)
    confidences = {item[0]: item[1] for item in all_extractions["property.plot_number"]}
    assert confidences["82"] >= 0.95
    assert confidences["9"] == 0.70
    conf, needs_review = party_role_confidence("clause_urdu", "seller")
    assert conf >= 0.88
    assert needs_review is False
    conf, needs_review = party_role_confidence("cnic_fallback", "seller")
    assert conf <= 0.45
    assert needs_review is True


def test_mutation_form_labels_are_rejected():
    for label in ("رجسٹریشن حوالہ", "منتقل الیہ", "/ منتقل الیہ", "منتقل کنندہ"):
        assert is_extraction_garbage(label, role="seller")[0] is True
        assert is_plausible_party_name(label, role="seller")[0] is False
        assert is_plausible_party_name(label, role="buyer")[0] is False


def test_mutation_is_not_sale_deed_from_one_keyword():
    mutation_text = (
        "انتقال نامہ / منتقلی\n"
        "منتقل کنندہ: ________\n"
        "منتقل الیہ: ________\n"
        "خریدار کا اندراج\n"
        "رجسٹریشن حوالہ"
    )
    assert classify_document("02_Mutation_Intiqal_URDU.pdf", mutation_text) == "mutation"
    assert allows_party_roles("mutation") is False
    pages = [PageOCR("doc-mut", "02_Mutation_Intiqal_URDU.pdf", 1, mutation_text)]
    roles = extract_party_roles_from_document(pages)
    assert not roles["seller_names"]
    assert not roles["buyer_names"]
