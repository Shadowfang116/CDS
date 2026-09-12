"""Prepare stored document pages for the shared OCR service."""

import base64
import io

from PIL import Image

from app.services.ocr import download_page_pdf, pdf_to_image
from app.services.storage import get_object_bytes

IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/tif"}


def _encode_png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def render_page_asset_to_base64_png(minio_key: str, content_type: str) -> str:
    """Render either an image object or a single-page PDF as a PNG payload."""
    if content_type in IMAGE_CONTENT_TYPES:
        image = Image.open(io.BytesIO(get_object_bytes(minio_key))).convert("RGB")
    else:
        image, _dpi_used = pdf_to_image(download_page_pdf(minio_key))
    return _encode_png(image)
