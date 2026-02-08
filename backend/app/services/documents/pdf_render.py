"""Utility to render PDF pages to images."""
import io
import logging
from typing import Optional
from PIL import Image
from pdf2image import convert_from_bytes

from app.services.storage import get_s3_client
from app.core.config import settings
from app.services.ocr import download_page_pdf

logger = logging.getLogger(__name__)


def get_page_image_bytes(minio_key_page_pdf: str) -> Optional[bytes]:
    """
    Get page image bytes from a page PDF stored in MinIO.
    
    Args:
        minio_key_page_pdf: MinIO key for the page PDF
        
    Returns:
        PNG image bytes, or None on error
    """
    try:
        # Download PDF bytes from MinIO
        pdf_bytes = download_page_pdf(minio_key_page_pdf)
        
        # Convert PDF to image
        # Use convert_from_bytes which handles single-page PDFs
        images = convert_from_bytes(
            pdf_bytes,
            dpi=getattr(settings, 'OCR_DPI', 200),
            fmt="png"
        )
        
        if not images:
            logger.warning(f"No images found in PDF: {minio_key_page_pdf}")
            return None
        
        # Get first (and should be only) image
        image: Image.Image = images[0]
        
        # Convert PIL Image to PNG bytes
        img_bytes_io = io.BytesIO()
        image.save(img_bytes_io, format='PNG')
        img_bytes = img_bytes_io.getvalue()
        
        return img_bytes
        
    except Exception as e:
        logger.error(f"Failed to render page image from {minio_key_page_pdf}: {str(e)}")
        return None

