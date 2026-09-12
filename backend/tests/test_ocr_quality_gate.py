from app.services.dossier_autofill import _score_page_text_quality, apply_candidate_quality_gate


def test_backend_quality_score_accepts_valid_sparse_urdu_text():
    score, level, warning = _score_page_text_quality("یہ ایک مختصر مگر درست اردو متن ہے", 0.95)

    assert level == "good"
    assert score >= 0.75
    assert warning is None


def test_high_risk_field_with_good_page_but_low_confidence_needs_review():
    _, needs_review, status, warning = apply_candidate_quality_gate(
        "property.plot_number",
        "82",
        "good",
        0.60,
        None,
    )

    assert needs_review is True
    assert status == "needs_review"
    assert "confidence" in (warning or "").lower()
