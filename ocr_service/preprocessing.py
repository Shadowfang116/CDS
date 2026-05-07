import cv2
import numpy as np

_DENOISE_MAX_PIXELS = 4_000_000


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def _adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )


def _deskew(binary: np.ndarray) -> np.ndarray:
    moments = cv2.moments(255 - binary)
    if abs(moments["mu20"] - moments["mu02"]) < 1e-5:
        return binary

    angle = 0.5 * np.arctan2(2.0 * moments["mu11"], moments["mu20"] - moments["mu02"])
    angle_degrees = float(np.degrees(angle))
    if abs(angle_degrees) < 0.1 or abs(angle_degrees) > 15:
        return binary

    height, width = binary.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    return cv2.warpAffine(
        binary,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _should_denoise(image: np.ndarray) -> bool:
    height, width = image.shape[:2]
    return height * width <= _DENOISE_MAX_PIXELS


def preprocess_page(image: np.ndarray) -> np.ndarray:
    gray = _to_grayscale(image)
    thresholded = _adaptive_threshold(gray)
    deskewed = _deskew(thresholded)
    if _should_denoise(deskewed):
        processed = cv2.fastNlMeansDenoising(deskewed, None, 18, 7, 21)
    else:
        processed = deskewed
    normalized = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX)
    return normalized
