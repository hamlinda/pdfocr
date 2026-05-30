import logging
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def is_pdf_searchable(pdf_path: Path, min_chars: int = 20) -> bool:
    """
    Checks if a PDF has extractable text (i.e. is searchable / already OCR'd).
    Returns True if at least min_chars of alphanumeric characters are extractable.
    Returns False if the PDF has no readable text.
    Raises an exception if the file cannot be opened or parsed.
    """
    try:
        reader = PdfReader(pdf_path)
        total_text_len = 0
        
        # Check if the PDF has pages
        if not reader.pages:
            logger.warning(f"PDF has no pages: {pdf_path}")
            return False
            
        for page in reader.pages:
            text = page.extract_text()
            if text:
                # Strip and clean text to get actual text content length (ignoring spaces/newlines)
                cleaned_text = "".join(c for c in text if c.isalnum())
                total_text_len += len(cleaned_text)
                if total_text_len >= min_chars:
                    return True
                    
        return total_text_len >= min_chars
    except Exception as e:
        logger.error(f"Error checking PDF readability for {pdf_path}: {e}")
        raise
