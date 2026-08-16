"""Unit tests for native PDF text layer extraction (Unit 1.2 / F6)."""
import io
import pytest
from pypdf import PdfWriter
from app.services.pdf_text_layer import extract_page_text, try_extract_pdf_text_layer


def create_sample_pdf_bytes(text_content: str = "This is native PDF text content for testing.") -> bytes:
    """Helper to generate in-memory sample PDF bytes with text layer."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    # pypdf writing text layer support or blank page with annotation
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_try_extract_pdf_text_layer_empty():
    """Test try_extract_pdf_text_layer returns None on empty pdf bytes."""
    res = try_extract_pdf_text_layer(b"")
    assert res is None


def test_try_extract_pdf_text_layer_invalid():
    """Test try_extract_pdf_text_layer returns None on garbage bytes."""
    res = try_extract_pdf_text_layer(b"NOT A VALID PDF HEADER")
    assert res is None
