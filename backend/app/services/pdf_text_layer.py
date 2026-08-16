"""Phase 8: PDF native text layer extraction for hybrid OCR pipeline."""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

logger = logging.getLogger(__name__)


@dataclass
class PdfTextExtractResult:
    """Result of PDF text extraction."""
    text: str
    metadata: Dict[str, Any]
    ok: bool


def extract_page_text_pymupdf(pdf_path:
    str, page_number: int) -> PdfTextExtractResult:
    """
    Extract native text from a PDF page using PyMuPDF (fitz).
    
    Args:
        pdf_path: Path to PDF file
        page_number: 0-based page number
    
    Returns:
        PdfTextExtractResult with text, metadata, and ok status
    """
    t_start = time.time()
    
    try:
        import fitz  # PyMuPDF
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            
            if page_number < 0 or page_number >= len(doc):
                return PdfTextExtractResult(
                    text="",
                    metadata={
                        "engine": "pymupdf",
                        "error": f"page_number {page_number} out of range (0-{len(doc)-1})",
                        "extract_ms": (time.time() - t_start) * 1000,
                    },
                    ok=False,
                )
            
            page = doc[page_number]
            
            # Extract plain text
            text = page.get_text("text")
            
            # Extract blocks for richer metadata
            blocks = page.get_text("blocks") or []
            
            extract_ms = (time.time() - t_start) * 1000
            
            metadata = {
                "engine": "pymupdf",
                "chars": len(text),
                "blocks": len(blocks) if isinstance(blocks, list) else 0,
                "extract_ms": extract_ms,
            }
            
            return PdfTextExtractResult(
                text=text,
                metadata=metadata,
                ok=True,
            )
            
        finally:
            if doc:
                doc.close()
                
    except ImportError:
        return PdfTextExtractResult(
            text="",
            metadata={
                "engine": "pymupdf",
                "error": "PyMuPDF (fitz) not installed",
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=False,
        )
    except Exception as e:
        error_msg = str(e)[:200]
        logger.warning(f"PyMuPDF extraction failed for page {page_number}: {error_msg}")
        return PdfTextExtractResult(
            text="",
            metadata={
                "engine": "pymupdf",
                "error": error_msg,
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=False,
        )


def extract_page_text_pdfminer(pdf_path:
    str, page_number: int) -> PdfTextExtractResult:
    """
    Extract native text from a PDF page using pdfminer.six.
    
    Args:
        pdf_path: Path to PDF file
        page_number: 0-based page number
    
    Returns:
        PdfTextExtractResult with text, metadata, and ok status
    """
    t_start = time.time()
    
    try:
        from pdfminer.high_level import extract_text
        from pdfminer.layout import LAParams
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
        from pdfminer.converter import TextConverter
        import io
        
        # Open PDF file
        with open(pdf_path, 'rb') as file:
            # Create resource manager and text converter
            rsrcmgr = PDFResourceManager()
            output_string = io.StringIO()
            laparams = LAParams()
            device = TextConverter(rsrcmgr, output_string, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            # Get specific page
            pages = list(PDFPage.get_pages(file))
            if page_number < 0 or page_number >= len(pages):
                return PdfTextExtractResult(
                    text="",
                    metadata={
                        "engine": "pdfminer",
                        "error": f"page_number {page_number} out of range (0-{len(pages)-1})",
                        "extract_ms": (time.time() - t_start) * 1000,
                    },
                    ok=False,
                )
            
            # Process the specific page
            interpreter.process_page(pages[page_number])
            text = output_string.getvalue()
            
            device.close()
            output_string.close()
            
            extract_ms = (time.time() - t_start) * 1000
            
            metadata = {
                "engine": "pdfminer",
                "chars": len(text),
                "extract_ms": extract_ms,
            }
            
            return PdfTextExtractResult(
                text=text,
                metadata=metadata,
                ok=True,
            )
            
    except ImportError:
        return PdfTextExtractResult(
            text="",
            metadata={
                "engine": "pdfminer",
                "error": "pdfminer.six not installed",
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=False,
        )
    except Exception as e:
        error_msg = str(e)[:200]
        logger.warning(f"pdfminer extraction failed for page {page_number}: {error_msg}")
        return PdfTextExtractResult(
            text="",
            metadata={
                "engine": "pdfminer",
                "error": error_msg,
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=False,
        )


def extract_page_text_pypdf(pdf_path: str, page_number: int) -> PdfTextExtractResult:
    """Extract native text from a PDF page using pypdf."""
    t_start = time.time()
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if page_number < 0 or page_number >= len(reader.pages):
            return PdfTextExtractResult(
                text="",
                metadata={
                    "engine": "pypdf",
                    "error": f"page_number {page_number} out of range (0-{len(reader.pages)-1})",
                    "extract_ms": (time.time() - t_start) * 1000,
                },
                ok=False,
            )
        page = reader.pages[page_number]
        text = page.extract_text() or ""
        return PdfTextExtractResult(
            text=text,
            metadata={
                "engine": "pypdf",
                "chars": len(text),
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=True,
        )
    except Exception as e:
        error_msg = str(e)[:200]
        logger.warning(f"pypdf extraction failed for page {page_number}: {error_msg}")
        return PdfTextExtractResult(
            text="",
            metadata={
                "engine": "pypdf",
                "error": error_msg,
                "extract_ms": (time.time() - t_start) * 1000,
            },
            ok=False,
        )


def extract_page_text(pdf_path: str, page_number: int, engine: str = "pypdf") -> PdfTextExtractResult:
    """
    Extract native text from a PDF page using the specified engine.
    
    Args:
        pdf_path: Path to PDF file
        page_number: 0-based page number
        engine: "pypdf", "pymupdf", or "pdfminer"
    
    Returns:
        PdfTextExtractResult with text, metadata, and ok status
    """
    if engine == "pypdf":
        res = extract_page_text_pypdf(pdf_path, page_number)
        if res.ok and res.text.strip():
            return res
        # Fall back to pymupdf / pdfminer if available
        return extract_page_text_pymupdf(pdf_path, page_number)
    elif engine == "pymupdf":
        return extract_page_text_pymupdf(pdf_path, page_number)
    elif engine == "pdfminer":
        return extract_page_text_pdfminer(pdf_path, page_number)
def try_extract_pdf_text_layer(pdf_bytes: bytes, page_number: int = 0) -> Optional[Dict[str, Any]]:
    """
    Attempts native PDF text extraction. Returns text and quality metadata if successful.
    """
    if not pdf_bytes or len(pdf_bytes) == 0:
        return None
    try:
        from pypdf import PdfReader
        import io
        from app.core.config import settings
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if page_number < 0 or page_number >= len(reader.pages):
            return None
        text = (reader.pages[page_number].extract_text() or "").strip()
        min_threshold = getattr(settings, "OCR_LOW_CHAR_COUNT_THRESHOLD", 50)
        if len(text) >= min_threshold:
            return {
                "text": text,
                "confidence": 0.99,
                "quality_level": "good",
                "engine_used": "pdf_text_layer_pypdf",
                "extracted_chars": len(text),
            }
    except Exception as e:
        logger.debug(f"PDF text layer extraction fallback: {e}")
    return None

