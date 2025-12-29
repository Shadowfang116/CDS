"""OCR service for extracting text from PDF pages using Tesseract."""
import io
import logging
from typing import Tuple, Optional

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.services.storage import get_s3_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """OCR processing error."""
    pass


def download_page_pdf(minio_key: str) -> bytes:
    """Download page PDF bytes from MinIO."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=minio_key)
        return response["Body"].read()
    except Exception as e:
        raise OCRError(f"Failed to download PDF from MinIO: {e}")


def pdf_to_image(pdf_bytes: bytes) -> Image.Image:
    """Convert PDF bytes to PIL Image using poppler's pdftoppm."""
    try:
        # Convert PDF to list of images (should be single page)
        images = convert_from_bytes(pdf_bytes, dpi=300, fmt="png")
        if not images:
            raise OCRError("No pages found in PDF")
        return images[0]  # Return first page (single-page PDF)
    except Exception as e:
        raise OCRError(f"Failed to convert PDF to image: {e}")


def run_tesseract(image: Image.Image) -> Tuple[str, Optional[float]]:
    """
    Run Tesseract OCR on an image.
    Returns (text, confidence_score).
    Confidence is a rough heuristic based on Tesseract output.
    """
    try:
        # Get OCR text
        text = pytesseract.image_to_string(image, lang="eng")
        
        # Get confidence data for heuristic
        confidence = None
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data.get("conf", []) if c != "-1" and str(c).isdigit()]
            if confidences:
                confidence = sum(confidences) / len(confidences)
        except Exception:
            pass  # Confidence is optional
        
        return text.strip(), confidence
    except Exception as e:
        raise OCRError(f"Tesseract OCR failed: {e}")


def ocr_page_pdf(minio_key: str) -> Tuple[str, Optional[float]]:
    """
    Full OCR pipeline for a page PDF stored in MinIO.
    
    Args:
        minio_key: The MinIO key for the page PDF.
        
    Returns:
        Tuple of (extracted_text, confidence_score)
        
    Raises:
        OCRError: If any step fails.
    """
    # Step 1: Download PDF from MinIO
    pdf_bytes = download_page_pdf(minio_key)
    
    # Step 2: Convert PDF to image
    image = pdf_to_image(pdf_bytes)
    
    # Step 3: Run Tesseract OCR
    text, confidence = run_tesseract(image)
    
    return text, confidence

