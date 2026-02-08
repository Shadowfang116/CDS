"""Thumbnail generation service for document pages."""
import io
import logging
from PIL import Image
from pdf2image import convert_from_bytes

from app.services.storage import get_s3_client, put_object_bytes
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_thumbnail_from_pdf(pdf_bytes: bytes, dpi: int = 72) -> bytes:
    """
    Generate a thumbnail PNG from PDF bytes.
    Returns PNG bytes (max 300px width, maintains aspect ratio).
    """
    try:
        # Convert PDF to image at low DPI
        images = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="png")
        if not images:
            raise ValueError("No pages found in PDF")
        
        image = images[0]
        
        # Resize to max 300px width (maintain aspect ratio)
        max_width = 300
        width, height = image.size
        if width > max_width:
            new_height = int(height * (max_width / width))
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PNG bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        raise


def ensure_thumbnail_exists(minio_key_pdf: str, minio_key_thumbnail: str) -> bool:
    """
    Generate and store thumbnail if it doesn't exist.
    Returns True if thumbnail was created, False if it already existed.
    """
    client = get_s3_client()
    
    # Check if thumbnail already exists
    try:
        client.head_object(Bucket=settings.MINIO_BUCKET, Key=minio_key_thumbnail)
        return False  # Already exists
    except Exception:
        pass  # Doesn't exist, create it
    
    # Download PDF
    try:
        response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=minio_key_pdf)
        pdf_bytes = response["Body"].read()
    except Exception as e:
        logger.error(f"Failed to download PDF for thumbnail: {e}")
        raise
    
    # Generate thumbnail
    thumbnail_bytes = generate_thumbnail_from_pdf(pdf_bytes)
    
    # Upload thumbnail
    put_object_bytes(minio_key_thumbnail, thumbnail_bytes, "image/png")
    
    return True  # Created

