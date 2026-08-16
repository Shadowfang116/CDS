"""Preprocessing pipeline for OCR service (F1 & F2 fixes)."""
import logging
import cv2
import numpy as np

logger = logging.getLogger("uvicorn.error")


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def _deskew_min_area_rect(gray: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
    """
    Correct deskew using minimum area bounding box of text contours (F2 fix).
    Capped at max_angle to avoid catastrophic false rotations.
    """
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return gray
        
        all_points = np.vstack(contours)
        rect = cv2.minAreaRect(all_points)
        angle = rect[2]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        if abs(angle) < 0.1 or abs(angle) > max_angle:
            return gray
        
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            gray,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception as e:
        logger.warning(f"Deskew failed: {e}, using original image")
        return gray


def _denoise_bilateral(gray: np.ndarray) -> np.ndarray:
    """Edge-preserving bilateral filter on grayscale image (F1 fix)."""
    try:
        return cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    except Exception as e:
        logger.warning(f"Bilateral denoise failed: {e}")
        return gray


def binarize_for_tesseract(gray: np.ndarray) -> np.ndarray:
    """
    Produces clean binarized image specifically for Tesseract engine pass.
    Uses dynamic block size scaled by image height.
    """
    height = gray.shape[0]
    block_size = max(15, (height // 60) | 1)  # Ensure odd integer >= 15
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        11,
    )


def upscale_low_dpi_image(gray: np.ndarray, min_target_side: int = 2400) -> np.ndarray:
    """
    Upscales low-resolution scans (e.g. 150 DPI) to ~300 DPI equivalent to restore cap height.
    """
    h, w = gray.shape[:2]
    long_side = max(h, w)
    if long_side < min_target_side:
        scale = min_target_side / float(long_side)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return gray


def detect_and_rotate_osd(gray: np.ndarray) -> np.ndarray:
    """
    Detects 90/180/270 degree page rotation via Tesseract OSD and rotates back.
    """
    try:
        import pytesseract
        osd_data = pytesseract.image_to_osd(gray, config="--psm 0 -l osd", output_type=pytesseract.Output.DICT)
        rotate_angle = osd_data.get("rotate", 0)
        if rotate_angle == 90:
            return cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotate_angle == 180:
            return cv2.rotate(gray, cv2.ROTATE_180)
        elif rotate_angle == 270:
            return cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
    except Exception as e:
        logger.debug(f"OSD orientation detection skipped or failed: {e}")
    return gray


def preprocess_page(image: np.ndarray) -> np.ndarray:
    """
    Main preprocessing pipeline for neural / VLM OCR engines.
    Preserves grayscale gradient details and thin Nastaliq strokes.
    Handles resolution upscaling and OSD rotation.
    """
    gray = _to_grayscale(image)
    upscaled = upscale_low_dpi_image(gray)
    rotated = detect_and_rotate_osd(upscaled)
    deskewed = _deskew_min_area_rect(rotated)
    denoised = _denoise_bilateral(deskewed)
    return denoised
