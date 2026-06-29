"""
Dedicated tax year extraction for Canadian T1 and NOA documents.
The taxation year is usually in the form header (e.g. large "2023" on page 1).
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Valid Canadian personal income tax years (extend as needed)
MIN_TAX_YEAR = 1990
MAX_TAX_YEAR = 2030

# Higher priority = more specific labels (English + French CRA forms)
TAX_YEAR_PATTERNS = [
    r"(?i)tax\s+year\s*[:\s]+(?:\()?(\d{4})(?:\))?",
    r"(?i)taxation\s+year\s*[:\s]+(?:\()?(\d{4})(?:\))?",
    r"(?i)for\s+the\s+(\d{4})\s+(?:taxation\s+)?year",
    r"(?i)year\s*[:\s]+(\d{4})\s*(?:tax|return|assessment|notice)",
    r"(?i)notice\s+of\s+assessment.*?(\d{4})",
    r"(?i)income\s+tax\s+and\s+benefit\s+return.*?(\d{4})",
    r"(?i)d[eé]claration\s+de\s+revenus.*?(\d{4})",
    r"(?i)avis\s+de\s+cotisation.*?(\d{4})",
    r"(?i)ann[eé]e\s+(?:d['\u2019]imposition|fiscale)\s*[:\s]+(\d{4})",
    r"(?i)ann[eé]e\s*[:\s]+(\d{4})",
    # T1/NOA header: standalone year on first lines (common on CRA forms)
    r"(?m)^\s*(\d{4})\s*$",
    r"(?i)\bT1(?:\s+GENERAL)?\s+.*?(\d{4})",
    r"(?i)\bNOA\b.*?(\d{4})",
]


def _valid_tax_year(year_str: str) -> Optional[str]:
    if not year_str or not year_str.isdigit() or len(year_str) != 4:
        return None
    year = int(year_str)
    if MIN_TAX_YEAR <= year <= MAX_TAX_YEAR:
        return year_str
    return None


def extract_tax_year_from_text(text: str, doc_type: str = "unknown") -> Optional[str]:
    """Extract taxation year from document text using labeled CRA patterns."""
    if not text or not text.strip():
        return None

    # Prefer first ~2500 chars (page 1 header) where tax year is printed prominently
    header = text[:2500]
    search_blocks = [header, text]

    for block in search_blocks:
        for pattern in TAX_YEAR_PATTERNS:
            match = re.search(pattern, block, re.MULTILINE | re.DOTALL)
            if match:
                year = _valid_tax_year(match.group(1))
                if year:
                    logger.info("Tax year %s found via pattern for %s", year, doc_type)
                    return year

    # Last resort: most frequent plausible year in header (avoid random dates)
    years = re.findall(r"\b(20\d{2})\b", header)
    if years:
        from collections import Counter

        for year, _count in Counter(years).most_common():
            valid = _valid_tax_year(year)
            if valid:
                logger.info("Tax year %s inferred from frequency in header for %s", valid, doc_type)
                return valid

    return None


def extract_tax_year_from_pdf_bytes(pdf_bytes: bytes, doc_type: str = "unknown") -> Optional[str]:
    """OCR page 1 only to read the large tax year printed in the form header."""
    if not pdf_bytes:
        return None

    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=1)
        if not images:
            return None

        page_text = pytesseract.image_to_string(images[0])
        year = extract_tax_year_from_text(page_text, doc_type)
        if year:
            logger.info("Tax year %s extracted from page-1 OCR for %s", year, doc_type)
        return year
    except Exception as exc:
        logger.warning("Page-1 OCR tax year extraction failed for %s: %s", doc_type, exc)
        return None
