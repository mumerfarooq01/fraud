"""
Document text extraction with OCR fallback for scanned/image PDFs.
"""

import logging
from typing import Tuple

from tax_validators.data_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

# Minimum usable characters from pdfplumber before trying OCR
MIN_TEXT_LENGTH = 150


def extract_document_text(pdf_path: str, pdf_bytes: bytes) -> Tuple[str, str]:
    """
    Extract text from a PDF using pdfplumber, then OCR if text is too sparse.

    Returns:
        (text, method) where method is 'pdfplumber', 'ocr', or 'none'
    """
    text = ""
    method = "none"

    try:
        text = extract_text_from_pdf(pdf_path) or ""
        if len(text.strip()) >= MIN_TEXT_LENGTH:
            logger.info(
                "Extracted %s characters from PDF via pdfplumber",
                len(text.strip()),
            )
            return text, "pdfplumber"
        logger.warning(
            "pdfplumber returned only %s characters — trying OCR",
            len(text.strip()),
        )
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)

    ocr_text = _extract_text_via_ocr(pdf_bytes)
    if len(ocr_text.strip()) >= MIN_TEXT_LENGTH:
        logger.info("Extracted %s characters from PDF via OCR", len(ocr_text.strip()))
        return ocr_text, "ocr"

    if text.strip():
        logger.warning(
            "OCR also sparse (%s chars) — using best available text",
            len(ocr_text.strip()),
        )
        return text if len(text) >= len(ocr_text) else ocr_text, "partial"

    if ocr_text.strip():
        return ocr_text, "ocr_partial"

    logger.error("No text could be extracted from PDF")
    return "", "none"


def _extract_text_via_ocr(pdf_bytes: bytes) -> str:
    """Convert PDF pages to images and run Tesseract OCR."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(pdf_bytes, dpi=300)
        parts = []

        for page_num, image in enumerate(images, 1):
            page_text = pytesseract.image_to_string(image)
            if page_text and page_text.strip():
                parts.append(f"\n--- Page {page_num} ---\n{page_text}")

        return "".join(parts)
    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        return ""
