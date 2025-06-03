import os
import logging
from typing import List, Optional
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

logger = logging.getLogger(__name__)


def get_pdf_page_count(pdf_path: str) -> int:
    """Get the total number of pages in a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        logger.error(f"Error reading PDF page count from {pdf_path}: {e}")
        return 0


def extract_text_from_page(pdf_path: str, page_number: int) -> str:
    """
    Extract text from a specific page (0-indexed).
    Returns empty string if extraction fails.
    """
    try:
        # pdfminer uses 0-indexed page numbers
        text = extract_text(pdf_path, page_numbers=[page_number], laparams=LAParams())
        return text or ""
    except Exception as e:
        logger.warning(f"Text extraction failed for page {page_number + 1} of {pdf_path}: {e}")
        return ""


def extract_text_from_pages(pdf_path: str, page_numbers: List[int]) -> dict:
    """
    Extract text from multiple pages.
    Returns dict with page numbers as keys and text as values.
    """
    result = {}
    for page_num in page_numbers:
        text = extract_text_from_page(pdf_path, page_num)
        result[f"page{page_num + 1}"] = text[:5000]  # Limit text length for storage
    
    return result


def split_pdf_into_pages(pdf_path: str) -> List[int]:
    """
    Get list of page indices for processing.
    Returns list of 0-indexed page numbers.
    """
    page_count = get_pdf_page_count(pdf_path)
    if page_count == 0:
        logger.error(f"Could not determine page count for {pdf_path}")
        return []
    
    return list(range(page_count))


def validate_pdf_file(pdf_path: str) -> bool:
    """Validate that the file exists and is a readable PDF."""
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file does not exist: {pdf_path}")
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        logger.error(f"File is not a PDF: {pdf_path}")
        return False
    
    try:
        reader = PdfReader(pdf_path)
        # Try to access the first page to ensure it's readable
        if len(reader.pages) > 0:
            _ = reader.pages[0]
        return True
    except Exception as e:
        logger.error(f"PDF file appears to be corrupted or unreadable: {pdf_path}, error: {e}")
        return False