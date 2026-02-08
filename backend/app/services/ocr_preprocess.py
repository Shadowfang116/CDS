"""Enhanced preprocessing for OCR images (Urdu OCR upgrade)."""
import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


def pil_to_cv2(img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR array."""
    if img.mode == 'RGB':
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    elif img.mode == 'L':
        return np.array(img)
    elif img.mode == 'RGBA':
        # Convert RGBA to RGB then to BGR
        rgb = np.array(img.convert('RGB'))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    else:
        # Convert to RGB first
        rgb = img.convert('RGB')
        return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def cv2_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV array to PIL Image (assumes grayscale if 2D, RGB if 3D)."""
    if len(arr.shape) == 2:
        return Image.fromarray(arr, mode='L')
    elif len(arr.shape) == 3 and arr.shape[2] == 3:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb, mode='RGB')
    else:
        # Fallback: convert to grayscale if needed
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
            return Image.fromarray(gray, mode='L')
        return Image.fromarray(arr)


def crop_margins(gray: np.ndarray, threshold_ratio: float = 0.95) -> np.ndarray:
    """
    Crop white/gray margins from image.
    
    Args:
        gray: Grayscale image array (0-255)
        threshold_ratio: Ratio to consider as background (0.95 = top 5% brightest pixels)
    
    Returns:
        Cropped grayscale array
    """
    try:
        # Find threshold value (top percentile)
        threshold_value = int(np.percentile(gray, threshold_ratio * 100))
        
        # Create binary mask: 1 for content, 0 for background
        # Invert: dark content = 1, light background = 0
        binary = (gray < threshold_value).astype(np.uint8) * 255
        
        # Find bounding box of content
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) == 0:
            # No content found, return original
            return gray
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        # Add small padding (2% of dimension, min 5px)
        h, w = gray.shape
        pad_y = max(5, int(h * 0.02))
        pad_x = max(5, int(w * 0.02))
        
        y_min = max(0, y_min - pad_y)
        x_min = max(0, x_min - pad_x)
        y_max = min(h, y_max + pad_y)
        x_max = min(w, x_max + pad_x)
        
        return gray[y_min:y_max, x_min:x_max]
    except Exception as e:
        logger.warning(f"Margin cropping failed: {e}, using original image")
        return gray


def remove_background_shading(gray: np.ndarray) -> np.ndarray:
    """
    Remove background shading using morphological operations.
    
    Uses morphological opening to estimate background, then normalizes.
    """
    try:
        # Large kernel for background estimation (approximate size of shading variations)
        kernel_size = max(21, int(min(gray.shape) * 0.1))  # 10% of smallest dimension, min 21
        if kernel_size % 2 == 0:
            kernel_size += 1  # Ensure odd
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        # Morphological opening to estimate background
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        
        # Normalize: divide by background and scale to 255
        # Add small epsilon to avoid division by zero
        normalized = cv2.divide(gray.astype(np.float32), (background.astype(np.float32) + 1), scale=255.0)
        normalized = np.clip(normalized, 0, 255).astype(np.uint8)
        
        return normalized
    except Exception as e:
        logger.warning(f"Background shading removal failed: {e}, using original image")
        return gray


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """
    Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    """
    try:
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced
    except Exception as e:
        logger.warning(f"Contrast enhancement failed: {e}, using original image")
        return gray


def denoise(gray: np.ndarray) -> np.ndarray:
    """
    Denoise image using bilateral filter (preserves edges).
    
    Alternative: fastNlMeansDenoising (slower but better quality)
    """
    try:
        # Bilateral filter: preserves edges while reducing noise
        denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        return denoised
    except Exception as e:
        logger.warning(f"Denoising failed: {e}, using original image")
        return gray


def deskew(gray: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
    """
    Deskew image by detecting rotation angle and correcting it.
    
    Args:
        gray: Grayscale image array
        max_angle: Maximum angle to correct (degrees), beyond this skip correction
    
    Returns:
        Deskewed grayscale array
    """
    try:
        # Method: Find minimum area bounding box of foreground pixels
        # Threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return gray
        
        # Combine all contours
        all_points = np.vstack(contours)
        
        # Find minimum area rectangle
        rect = cv2.minAreaRect(all_points)
        angle = rect[2]
        
        # Normalize angle: minAreaRect returns angle in range [-90, 0]
        # We want the angle needed to rotate to horizontal
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only correct if angle is significant but within max_angle
        if abs(angle) < 0.1 or abs(angle) > max_angle:
            return gray
        
        # Rotate image
        h, w = gray.shape
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new dimensions to avoid cropping
        cos_angle = np.abs(rotation_matrix[0, 0])
        sin_angle = np.abs(rotation_matrix[0, 1])
        new_w = int((h * sin_angle) + (w * cos_angle))
        new_h = int((h * cos_angle) + (w * sin_angle))
        
        # Adjust rotation matrix center
        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]
        
        # Apply rotation
        deskewed = cv2.warpAffine(gray, rotation_matrix, (new_w, new_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return deskewed
    except Exception as e:
        logger.warning(f"Deskew failed: {e}, using original image")
        return gray


def preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
    """
    Enhanced preprocessing pipeline for OCR.
    
    Pipeline order:
    1. Convert to grayscale
    2. Crop margins
    3. Remove background shading
    4. Enhance contrast (CLAHE)
    5. Denoise (bilateral filter)
    6. Deskew
    
    Args:
        pil_img: PIL Image (any mode)
    
    Returns:
        Preprocessed PIL Image (grayscale)
    """
    if not settings.OCR_ENABLE_ENHANCED_PREPROCESS:
        # Fallback to basic grayscale if disabled
        if pil_img.mode != 'L':
            return pil_img.convert('L')
        return pil_img
    
    try:
        # Convert to grayscale PIL first (if needed)
        if pil_img.mode != 'L':
            pil_img = pil_img.convert('L')
        
        # Convert to OpenCV array
        gray = np.array(pil_img)
        
        # Pipeline
        gray = crop_margins(gray)
        gray = remove_background_shading(gray)
        gray = enhance_contrast(gray)
        gray = denoise(gray)
        gray = deskew(gray)
        
        # Convert back to PIL
        return Image.fromarray(gray, mode='L')
        
    except Exception as e:
        logger.warning(f"Enhanced preprocessing failed: {e}, falling back to basic grayscale")
        # Fallback: just convert to grayscale
        if pil_img.mode != 'L':
            return pil_img.convert('L')
        return pil_img

