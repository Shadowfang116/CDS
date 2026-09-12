from app.services.ocr_eval import evaluate_ocr_result


def test_evaluate_ocr_result_returns_quality_and_accuracy_metrics() -> None:
    result = evaluate_ocr_result("یہ ایک متن ہے", gt_text="یہ ایک متن ہے")

    assert result["urdu_ratio"] > 0
    assert result["latin_ratio"] == 0
    assert result["garbage_ratio"] == 0
    assert result["whitespace_ratio"] > 0
    assert result["cer"] == 0
    assert result["wer"] == 0
    assert result["f1"] == 1


def test_evaluate_ocr_result_handles_mixed_text_quality_metrics() -> None:
    result = evaluate_ocr_result("ABC 123", gt_text="ABC 124")

    assert result["urdu_ratio"] == 0
    assert result["latin_ratio"] > 0
    assert result["garbage_ratio"] == 0
    assert 0 < result["cer"] < 1
    assert 0 < result["wer"] < 1
    assert 0 < result["f1"] < 1


def test_evaluate_ocr_result_uses_word_error_rate() -> None:
    result = evaluate_ocr_result("ABC 123", gt_text="ABC 124")

    assert result["wer"] == 0.5
