from app.services.extractions import compute_needs_review, get_field_value, LOW_CONFIDENCE_THRESHOLD


def test_low_confidence_flagging():
    assert compute_needs_review(0.1) is True
    assert compute_needs_review(LOW_CONFIDENCE_THRESHOLD - 0.01) is True
    assert compute_needs_review(LOW_CONFIDENCE_THRESHOLD + 0.01) is False
    assert compute_needs_review(None) is True
    assert compute_needs_review(0.95, is_low_quality=True) is True


def test_get_field_value_precedence():
    assert get_field_value("extracted", None, None) == "extracted"
    assert get_field_value("extracted", "edited", None) == "edited"
    assert get_field_value("extracted", None, "final") == "final"
    assert get_field_value(" ", " ", None) is None
