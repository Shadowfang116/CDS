import sys
from pathlib import Path

ocr_service_dir = Path(__file__).resolve().parent.parent.parent / "ocr_service"
sys.path.insert(0, str(ocr_service_dir))

import numpy as np
import pytest
from preprocessing import preprocess_page, _deskew_min_area_rect, binarize_for_tesseract


def test_preprocess_page_preserves_grayscale():
    """Verify preprocess_page outputs grayscale array (2D) without binarization."""
    synthetic_img = np.random.randint(0, 255, (2000, 3000, 3), dtype=np.uint8)
    processed = preprocess_page(synthetic_img)
    assert processed.ndim == 2
    assert processed.shape == (2000, 3000)
    # Ensure it's not binary (values exist across spectrum, not just 0 and 255)
    unique_vals = len(np.unique(processed))
    assert unique_vals > 2


def test_binarize_for_tesseract():
    """Verify binarize_for_tesseract produces 1-bit binary image."""
    gray_img = np.random.randint(0, 255, (200, 300), dtype=np.uint8)
    binary = binarize_for_tesseract(gray_img)
    assert set(np.unique(binary)).issubset({0, 255})


def test_deskew_min_area_rect():
    """Test minAreaRect deskew on synthetic image."""
    gray_img = np.ones((200, 300), dtype=np.uint8) * 255
    # Draw a line blob
    gray_img[90:110, 50:250] = 0
    deskewed = _deskew_min_area_rect(gray_img)
    assert deskewed.shape == (200, 300)


def test_upscale_low_dpi_image():
    """Test low-DPI upscaling function."""
    from preprocessing import upscale_low_dpi_image
    small_img = np.ones((500, 400), dtype=np.uint8) * 128
    upscaled = upscale_low_dpi_image(small_img, min_target_side=2400)
    assert max(upscaled.shape[:2]) == 2400
