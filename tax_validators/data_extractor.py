"""
PDF Data Extractor Module
Extracts text and structured data from Canadian tax documents using pdfplumber.
"""

import pdfplumber
import logging
import re
from typing import Dict, List, Optional, Union
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract all text from PDF file
    
    Args:
        pdf_file: PDF file path or BytesIO object
        
    Returns:
        Concatenated text from all pages
    """
    try:
        text_content = ""
        
        # Handle both file path and BytesIO object
        if isinstance(pdf_file, str):
            # File path
            with pdfplumber.open(pdf_file) as pdf:
                logger.info(f"Extracting text from PDF file: {pdf_file}")
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num} ---\n"
                        text_content += page_text
                    logger.info(f"Processed page {page_num}")
        else:
            # BytesIO object from Streamlit
            pdf_file.seek(0)  # Reset file pointer
            with pdfplumber.open(pdf_file) as pdf:
                logger.info("Extracting text from PDF BytesIO object")
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num} ---\n"
                        text_content += page_text
                    logger.info(f"Processed page {page_num}")
        
        logger.info(f"Successfully extracted {len(text_content)} characters")
        return text_content
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_tables_from_pdf(pdf_file) -> list:
    """
    Extract tables if present
    
    Args:
        pdf_file: PDF file path or BytesIO object
        
    Returns:
        List of table data
    """
    try:
        tables_data = []
        
        # Handle both file path and BytesIO object
        if isinstance(pdf_file, str):
            # File path
            with pdfplumber.open(pdf_file) as pdf:
                logger.info(f"Extracting tables from PDF file: {pdf_file}")
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_num, table in enumerate(page_tables, 1):
                            tables_data.append({
                                'page': page_num,
                                'table': table_num,
                                'data': table
                            })
                        logger.info(f"Found {len(page_tables)} tables on page {page_num}")
        else:
            # BytesIO object from Streamlit
            pdf_file.seek(0)  # Reset file pointer
            with pdfplumber.open(pdf_file) as pdf:
                logger.info("Extracting tables from PDF BytesIO object")
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_num, table in enumerate(page_tables, 1):
                            tables_data.append({
                                'page': page_num,
                                'table': table_num,
                                'data': table
                            })
                        logger.info(f"Found {len(page_tables)} tables on page {page_num}")
        
        logger.info(f"Successfully extracted {len(tables_data)} tables")
        return tables_data
        
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        raise Exception(f"Failed to extract tables from PDF: {str(e)}")

def get_page_count(pdf_file) -> int:
    """
    Get total number of pages
    
    Args:
        pdf_file: PDF file path or BytesIO object
        
    Returns:
        Page count
    """
    try:
        # Handle both file path and BytesIO object
        if isinstance(pdf_file, str):
            # File path
            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
                logger.info(f"PDF file {pdf_file} has {page_count} pages")
                return page_count
        else:
            # BytesIO object from Streamlit
            pdf_file.seek(0)  # Reset file pointer
            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
                logger.info(f"PDF BytesIO object has {page_count} pages")
                return page_count
                
    except Exception as e:
        logger.error(f"Error getting page count from PDF: {str(e)}")
        raise Exception(f"Failed to get page count from PDF: {str(e)}")

def extract_key_fields(pdf_text: str, doc_type: str) -> dict:
    """
    Extract specific fields based on document type
    
    Args:
        pdf_text: Extracted text from PDF
        doc_type: Document type ('T1' or 'NOA')
        
    Returns:
        Dictionary with extracted fields
    """
    try:
        logger.info(f"Extracting key fields for document type: {doc_type}")
        
        extracted_fields = {
            'sin': None,
            'name': None,
            'address': None,
            'refund_amount': None,
            'total_income': None,
            'net_income': None,
            'taxable_income': None,
            'federal_tax': None,
            'provincial_tax': None,
            'total_tax': None,
            'balance_owing': None,
            'filing_date': None,
            'assessment_date': None,
            'tax_year': None,
            'accountant_info': None
        }
        
        if doc_type.upper() == 'T1':
            extracted_fields.update(_extract_t1_fields(pdf_text))
        elif doc_type.upper() == 'NOA':
            extracted_fields.update(_extract_noa_fields(pdf_text))
        else:
            logger.warning(f"Unknown document type: {doc_type}")
        
        # Count successfully extracted fields
        extracted_count = sum(1 for value in extracted_fields.values() if value is not None)
        logger.info(f"Successfully extracted {extracted_count} fields")
        
        return extracted_fields
        
    except Exception as e:
        logger.error(f"Error extracting key fields: {str(e)}")
        raise Exception(f"Failed to extract key fields: {str(e)}")

def _extract_t1_fields(pdf_text: str) -> dict:
    """
    Extract specific fields from T1 Income Tax Return
    
    Args:
        pdf_text: Extracted text from T1 PDF
        
    Returns:
        Dictionary with T1-specific fields
    """
    fields = {}
    
    # Extract SIN (Social Insurance Number)
    sin_pattern = r'\b\d{3}\s*\d{3}\s*\d{3}\b'
    sin_match = re.search(sin_pattern, pdf_text)
    if sin_match:
        fields['sin'] = sin_match.group().replace(' ', '')
    
    # Extract name (look for common name patterns)
    name_patterns = [
        r'Name:\s*([A-Za-z\s,.-]+)',
        r'Last name:\s*([A-Za-z\s,.-]+)',
        r'First name:\s*([A-Za-z\s,.-]+)',
        r'Surname:\s*([A-Za-z\s,.-]+)'
    ]
    for pattern in name_patterns:
        name_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if name_match:
            fields['name'] = name_match.group(1).strip()
            break
    
    # Extract address (look for address patterns)
    address_patterns = [
        r'Address:\s*([^\n]+(?:\n[^\n]+)*)',
        r'Street address:\s*([^\n]+(?:\n[^\n]+)*)',
        r'Residential address:\s*([^\n]+(?:\n[^\n]+)*)'
    ]
    for pattern in address_patterns:
        address_match = re.search(pattern, pdf_text, re.IGNORECASE | re.MULTILINE)
        if address_match:
            fields['address'] = address_match.group(1).strip()
            break
    
    # Extract refund amount
    refund_patterns = [
        r'Refund:\s*\$?([\d,]+\.?\d*)',
        r'Amount refunded:\s*\$?([\d,]+\.?\d*)',
        r'Overpayment:\s*\$?([\d,]+\.?\d*)',
        r'Line 484:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in refund_patterns:
        refund_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if refund_match:
            fields['refund_amount'] = refund_match.group(1).replace(',', '')
            break
    
    # Extract total income
    income_patterns = [
        r'Total income.*?Line 150.*?\$?([\d,]+\.?\d*)',
        r'Line 150.*?\$?([\d,]+\.?\d*)',
        r'Total income:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in income_patterns:
        income_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if income_match:
            fields['total_income'] = income_match.group(1).replace(',', '')
            break
    
    # Extract net income
    net_income_patterns = [
        r'Net income.*?Line 236.*?\$?([\d,]+\.?\d*)',
        r'Line 236.*?\$?([\d,]+\.?\d*)',
        r'Net income:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in net_income_patterns:
        net_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if net_match:
            fields['net_income'] = net_match.group(1).replace(',', '')
            break
    
    # Extract taxable income
    taxable_patterns = [
        r'Taxable income.*?Line 260.*?\$?([\d,]+\.?\d*)',
        r'Line 260.*?\$?([\d,]+\.?\d*)',
        r'Taxable income:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in taxable_patterns:
        taxable_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if taxable_match:
            fields['taxable_income'] = taxable_match.group(1).replace(',', '')
            break
    
    # Extract federal tax
    federal_tax_patterns = [
        r'Federal tax.*?Line 420.*?\$?([\d,]+\.?\d*)',
        r'Line 420.*?\$?([\d,]+\.?\d*)',
        r'Federal tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in federal_tax_patterns:
        fed_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if fed_match:
            fields['federal_tax'] = fed_match.group(1).replace(',', '')
            break
    
    # Extract provincial tax
    provincial_tax_patterns = [
        r'Provincial tax.*?Line 428.*?\$?([\d,]+\.?\d*)',
        r'Line 428.*?\$?([\d,]+\.?\d*)',
        r'Provincial tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in provincial_tax_patterns:
        prov_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if prov_match:
            fields['provincial_tax'] = prov_match.group(1).replace(',', '')
            break
    
    # Extract total tax
    total_tax_patterns = [
        r'Total tax.*?Line 435.*?\$?([\d,]+\.?\d*)',
        r'Line 435.*?\$?([\d,]+\.?\d*)',
        r'Total tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in total_tax_patterns:
        total_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if total_match:
            fields['total_tax'] = total_match.group(1).replace(',', '')
            break
    
    # Extract balance owing
    balance_patterns = [
        r'Balance owing.*?\$?([\d,]+\.?\d*)',
        r'Amount owing:\s*\$?([\d,]+\.?\d*)',
        r'Balance due:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in balance_patterns:
        balance_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if balance_match:
            fields['balance_owing'] = balance_match.group(1).replace(',', '')
            break
    
    # Extract filing date
    filing_date_patterns = [
        r'Filing date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Date filed:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Filed on:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    ]
    for pattern in filing_date_patterns:
        filing_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if filing_match:
            fields['filing_date'] = filing_match.group(1)
            break
    
    # Extract tax year
    year_pattern = r'(?:20\d{2}|19\d{2})'
    year_match = re.search(year_pattern, pdf_text)
    if year_match:
        fields['tax_year'] = year_match.group()
    
    # Extract accountant info
    accountant_patterns = [
        r'Prepared by:\s*([^\n]+)',
        r'Accountant:\s*([^\n]+)',
        r'Tax preparer:\s*([^\n]+)'
    ]
    for pattern in accountant_patterns:
        accountant_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if accountant_match:
            fields['accountant_info'] = accountant_match.group(1).strip()
            break
    
    return fields

def _extract_noa_fields(pdf_text: str) -> dict:
    """
    Extract specific fields from Notice of Assessment (NOA)
    
    Args:
        pdf_text: Extracted text from NOA PDF
        
    Returns:
        Dictionary with NOA-specific fields
    """
    fields = {}
    
    # Extract SIN (last 4 digits for NOA)
    sin_pattern = r'\b\d{3}\s*\d{3}\s*\d{3}\b'
    sin_match = re.search(sin_pattern, pdf_text)
    if sin_match:
        fields['sin'] = sin_match.group().replace(' ', '')
    
    # Extract name (look for common name patterns)
    name_patterns = [
        r'Name:\s*([A-Za-z\s,.-]+)',
        r'Taxpayer name:\s*([A-Za-z\s,.-]+)',
        r'Assessed for:\s*([A-Za-z\s,.-]+)'
    ]
    for pattern in name_patterns:
        name_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if name_match:
            fields['name'] = name_match.group(1).strip()
            break
    
    # Extract address (look for address patterns)
    address_patterns = [
        r'Address:\s*([^\n]+(?:\n[^\n]+)*)',
        r'Mailing address:\s*([^\n]+(?:\n[^\n]+)*)',
        r'Residential address:\s*([^\n]+(?:\n[^\n]+)*)'
    ]
    for pattern in address_patterns:
        address_match = re.search(pattern, pdf_text, re.IGNORECASE | re.MULTILINE)
        if address_match:
            fields['address'] = address_match.group(1).strip()
            break
    
    # Extract refund amount
    refund_patterns = [
        r'Refund:\s*\$?([\d,]+\.?\d*)',
        r'Amount refunded:\s*\$?([\d,]+\.?\d*)',
        r'Overpayment:\s*\$?([\d,]+\.?\d*)',
        r'Refund amount:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in refund_patterns:
        refund_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if refund_match:
            fields['refund_amount'] = refund_match.group(1).replace(',', '')
            break
    
    # Extract assessed total income
    income_patterns = [
        r'Assessed total income:\s*\$?([\d,]+\.?\d*)',
        r'Total income assessed:\s*\$?([\d,]+\.?\d*)',
        r'Income assessed:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in income_patterns:
        income_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if income_match:
            fields['total_income'] = income_match.group(1).replace(',', '')
            break
    
    # Extract assessed net income
    net_income_patterns = [
        r'Assessed net income:\s*\$?([\d,]+\.?\d*)',
        r'Net income assessed:\s*\$?([\d,]+\.?\d*)',
        r'Net income:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in net_income_patterns:
        net_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if net_match:
            fields['net_income'] = net_match.group(1).replace(',', '')
            break
    
    # Extract assessed taxable income
    taxable_patterns = [
        r'Assessed taxable income:\s*\$?([\d,]+\.?\d*)',
        r'Taxable income assessed:\s*\$?([\d,]+\.?\d*)',
        r'Taxable income:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in taxable_patterns:
        taxable_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if taxable_match:
            fields['taxable_income'] = taxable_match.group(1).replace(',', '')
            break
    
    # Extract assessed federal tax
    federal_tax_patterns = [
        r'Assessed federal tax:\s*\$?([\d,]+\.?\d*)',
        r'Federal tax assessed:\s*\$?([\d,]+\.?\d*)',
        r'Federal tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in federal_tax_patterns:
        fed_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if fed_match:
            fields['federal_tax'] = fed_match.group(1).replace(',', '')
            break
    
    # Extract assessed provincial tax
    provincial_tax_patterns = [
        r'Assessed provincial tax:\s*\$?([\d,]+\.?\d*)',
        r'Provincial tax assessed:\s*\$?([\d,]+\.?\d*)',
        r'Provincial tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in provincial_tax_patterns:
        prov_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if prov_match:
            fields['provincial_tax'] = prov_match.group(1).replace(',', '')
            break
    
    # Extract assessed total tax
    total_tax_patterns = [
        r'Assessed total tax:\s*\$?([\d,]+\.?\d*)',
        r'Total tax assessed:\s*\$?([\d,]+\.?\d*)',
        r'Total tax:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in total_tax_patterns:
        total_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if total_match:
            fields['total_tax'] = total_match.group(1).replace(',', '')
            break
    
    # Extract balance owing
    balance_patterns = [
        r'Balance owing:\s*\$?([\d,]+\.?\d*)',
        r'Amount owing:\s*\$?([\d,]+\.?\d*)',
        r'Balance due:\s*\$?([\d,]+\.?\d*)'
    ]
    for pattern in balance_patterns:
        balance_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if balance_match:
            fields['balance_owing'] = balance_match.group(1).replace(',', '')
            break
    
    # Extract assessment date
    assessment_date_patterns = [
        r'Assessment date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Date of assessment:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Assessed on:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Notice date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    ]
    for pattern in assessment_date_patterns:
        assessment_match = re.search(pattern, pdf_text, re.IGNORECASE)
        if assessment_match:
            fields['assessment_date'] = assessment_match.group(1)
            break
    
    # Extract tax year
    year_pattern = r'(?:20\d{2}|19\d{2})'
    year_match = re.search(year_pattern, pdf_text)
    if year_match:
        fields['tax_year'] = year_match.group()
    
    return fields
