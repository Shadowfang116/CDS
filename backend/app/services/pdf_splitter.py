from io import BytesIO
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter


class PDFSplitError(Exception):
    """Raised when PDF splitting fails."""
    pass


def split_pdf(pdf_bytes: bytes) -> Tuple[int, List[Tuple[int, bytes]]]:
    """
    Split a PDF into individual pages.
    
    Args:
        pdf_bytes: The raw PDF bytes
        
    Returns:
        Tuple of (page_count, list of (page_number, page_pdf_bytes))
        Page numbers are 1-based.
        
    Raises:
        PDFSplitError: If the PDF is invalid or cannot be split
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        
        if page_count == 0:
            raise PDFSplitError("PDF has no pages")
        
        pages: List[Tuple[int, bytes]] = []
        
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)
            
            output = BytesIO()
            writer.write(output)
            output.seek(0)
            
            # Page numbers are 1-based
            pages.append((i + 1, output.read()))
        
        return page_count, pages
        
    except Exception as e:
        if isinstance(e, PDFSplitError):
            raise
        raise PDFSplitError(f"Failed to split PDF: {str(e)}") from e

