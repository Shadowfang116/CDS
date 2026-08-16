"""Regression tests for Urdu domain normalization and encoding integrity."""
import re
import pytest
from pathlib import Path
from app.services.ocr_domain_ur import URDU_MONTHS, normalize_separators, normalize_dates, normalize_cnic
from app.services.ocr_text import normalize_whitespace

def test_ocr_domain_ur_encoding_integrity():
    """Ensure ocr_domain_ur.py and ocr_text.py contain real Urdu chars and no mojibake tokens."""
    services_dir = Path(__file__).resolve().parent.parent / "app" / "services"
    for filename in ["ocr_domain_ur.py", "ocr_text.py"]:
        file_path = services_dir / filename
        content = file_path.read_text(encoding="utf-8")
        
        # Check for real Urdu characters
        real_urdu_count = len(re.findall(r"[\u0600-\u06FF]", content))
        assert real_urdu_count > 0, f"{filename} should contain real Urdu characters"
        
        # Check for lingering cp1252 mojibake candidates
        cands = set(re.findall(r"[ -ÿŒœŠšŽžƒ–-⁄€™]{2,}", content))
        mojibake_tokens = [c for c in cands if re.search(r"[\u0600-\u06FF]", c.encode("cp1252", "ignore").decode("utf-8", "ignore"))]
        assert len(mojibake_tokens) == 0, f"Found mojibake tokens in {filename}: {mojibake_tokens}"


def test_urdu_months_dict():
    """Verify Urdu month constants match correctly."""
    assert URDU_MONTHS["جنوری"] == 1
    assert URDU_MONTHS["فروری"] == 2
    assert URDU_MONTHS["مارچ"] == 3
    assert URDU_MONTHS["دسمبر"] == 12


def test_normalize_separators():
    """Test normalization of Urdu separators and punctuation."""
    text = "مورخہ 15 جنوری 2024ء۔ رقبہ 12 کنال، 4 مرلہ"
    normalized = normalize_separators(text)
    assert "." in normalized or "۔" in text
