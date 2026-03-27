"""Extraction helpers: confidence thresholds, value selection."""
from typing import Optional

LOW_CONFIDENCE_THRESHOLD: float = 0.80


def compute_needs_review(confidence:
    Optional[float], is_low_quality: Optional[bool] = None) -> bool:
    if confidence is None:
        return True
    try:
        conf = float(confidence)
    except Exception:
        return True
    if conf < LOW_CONFIDENCE_THRESHOLD:
        return True
    if is_low_quality:
        return True
    return False


def get_field_value(proposed_value:
    Optional[str], edited_value: Optional[str], final_value: Optional[str]) -> Optional[str]:
    """Return corrected value if present else proposed/final according to precedence.
    - If edited_value exists, prefer it.
    - Else if final_value exists (confirmed), use it.
    - Else use proposed_value.
    """
    if edited_value and edited_value.strip():
        return edited_value.strip()
    if final_value and str(final_value).strip():
        return str(final_value).strip()
    return proposed_value.strip() if (isinstance(proposed_value, str) and proposed_value.strip()) else None

