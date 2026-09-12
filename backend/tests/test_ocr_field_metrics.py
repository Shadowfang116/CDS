from app.services.ocr_eval import evaluate_field_predictions, normalize_field_value


def test_normalize_field_value_handles_amounts_and_urdu_digits():
    assert normalize_field_value("روپے ۱٬۸۵۰٬۰۰۰/-", "amount") == "1850000"
    assert normalize_field_value("  4  Kanal ", "area") == "4 kanal"


def test_evaluate_field_predictions_separates_exact_and_normalized_matches():
    result = evaluate_field_predictions(
        references=[
            {"document_id": "doc", "page": 1, "field": "amount", "reference_value": "1850000", "normalization": "amount"},
            {"document_id": "doc", "page": 1, "field": "plot_number", "reference_value": "82", "normalization": "identifier"},
        ],
        predictions=[
            {"document_id": "doc", "page": 1, "field": "amount", "predicted_value": "PKR 1,850,000", "confidence": 0.94, "source_page": 1, "snippet": "رقم PKR 1,850,000"},
            {"document_id": "doc", "page": 1, "field": "plot_number", "predicted_value": "83", "confidence": 0.96, "source_page": 1, "snippet": "پلاٹ نمبر 83"},
        ],
    )

    assert result["fields_total"] == 2
    assert result["normalized_matches"] == 1
    assert result["exact_matches"] == 0
    assert result["false_positives"] == 1
    assert result["missing_evidence_links"] == 0
