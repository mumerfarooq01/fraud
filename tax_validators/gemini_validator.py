"""
Gemini LLM Validator Module
Modular LLM-based validation using Google Gemini API for Canadian tax documents.
"""

import google.generativeai as genai
import os
import json
import logging
import time
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_gemini():
    """
    Initialize Gemini API with key from env
    
    Returns:
        Configured Gemini model instance
    """
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        logger.info("Gemini API initialized successfully")
        return model
        
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {str(e)}")
        raise Exception(f"Gemini API initialization failed: {str(e)}")

def extract_structured_data_t1(text: str, model) -> dict:
    """
    Use Gemini to extract structured data from T1 document
    
    Args:
        text: Extracted text from T1 document
        model: Initialized Gemini model
        
    Returns:
        Structured dictionary with extracted data
    """
    prompt = """
    Extract the following information from this Canadian T1 Income Tax Return document:
    
    1. Social Insurance Number (SIN)
    2. Full Name
    3. Complete Address
    4. Refund Amount or Balance Owing 
    5. Total Income 
    6. Net Income 
    7. Taxable Income
    8. Tax Deducted 
    9. Tax Paid by Instalments 
    10. Name of tax professional (if present)
    11. Tax professional Phone Number (if present just extract the number not text associated with the number like "ext.")
    12. Date of Filing (signature date)
    
    Return ONLY a JSON object with these EXACT field names:
    {{
      "sin": "value or null",
      "full_name": "value or null",
      "address": "value or null",
      "refund_amount": "value or null",
      "total_income": "value or null",
      "net_income": "value or null",
      "taxable_income": "value or null",
      "tax_deducted": "value or null",
      "tax_paid_instalments": "value or null",
      "accountant_name": "value or null",
      "accountant_phone": "value or null",
      "filing_date": "value or null"
    }}
    
    Use null for missing fields. Return ONLY the JSON, no other text.
    
    Document text:
    {text}
    """.format(text=text)
    
    try:
        logger.info("Extracting structured data from T1 document using Gemini")
        
        # Send to Gemini with retry logic
        response = _send_gemini_request(model, prompt, max_retries=3)
        
        # Parse JSON response
        structured_data = _parse_json_response(response)
        
        logger.info(f"Successfully extracted {len([k for k, v in structured_data.items() if v is not None])} fields from T1")
        return structured_data
        
    except Exception as e:
        logger.error(f"Error extracting T1 structured data: {str(e)}")
        return {
            "sin": None,
            "full_name": None,
            "address": None,
            "refund_amount": None,
            "total_income": None,
            "net_income": None,
            "taxable_income": None,
            "tax_deducted": None,
            "tax_paid_instalments": None,
            "accountant_name": None,
            "accountant_phone": None,
            "filing_date": None
        }

def extract_structured_data_noa(text: str, model) -> dict:
    """
    Use Gemini to extract structured data from NOA document
    
    Args:
        text: Extracted text from NOA document
        model: Initialized Gemini model
        
    Returns:
        Structured dictionary with extracted data
    """
    prompt = """
    Extract the following information from this Canadian Notice of Assessment document:
    
    1. Social Insurance Number (last 4 digits visible, format: XXX XX3 XXX)
    2. Full Name
    3. Complete Address
    4. Refund Amount (shown in account summary)
    5. Total Income
    6. Net Income
    7. Taxable Income
    8. Total Income Tax Deducted
    9. Tax Paid by Instalments
    10. Date Issued (assessment date)
    
    Return ONLY a JSON object with these EXACT field names:
    {{
      "sin": "value or null",
      "full_name": "value or null",
      "address": "value or null",
      "refund_amount": "value or null",
      "total_income": "value or null",
      "net_income": "value or null",
      "taxable_income": "value or null",
      "tax_deducted": "value or null",
      "tax_paid_instalments": "value or null",
      "date_issued": "value or null"
    }}
    
    Use null for missing fields. Return ONLY the JSON, no other text.
    
    Document text:
    {text}
    """.format(text=text)
    
    try:
        logger.info("Extracting structured data from NOA document using Gemini")
        
        # Send to Gemini with retry logic
        response = _send_gemini_request(model, prompt, max_retries=3)
        
        # Parse JSON response
        structured_data = _parse_json_response(response)
        
        logger.info(f"Successfully extracted {len([k for k, v in structured_data.items() if v is not None])} fields from NOA")
        return structured_data
        
    except Exception as e:
        logger.error(f"Error extracting NOA structured data: {str(e)}")
        return {
            "sin": None,
            "full_name": None,
            "address": None,
            "refund_amount": None,
            "total_income": None,
            "net_income": None,
            "taxable_income": None,
            "tax_deducted": None,
            "tax_paid_instalments": None,
            "date_issued": None
        }

def validate_cross_document(t1_data: dict, noa_data: dict, model) -> dict:
    """
    Validate consistency between T1 and NOA
    
    Args:
        t1_data: Structured data from T1 document
        noa_data: Structured data from NOA document
        model: Initialized Gemini model
        
    Returns:
        Validation results dictionary
    """
    prompt = """
    Compare these two Canadian tax documents and identify discrepancies:
    
    T1 Data: {t1_data}
    NOA Data: {noa_data}
    
    Check for:
    1. SIN matching (last 4 digits)
    2. Name matching (exact or minor variations)
    3. Address matching (exact or minor variations)
    4. Refund amount matching
    5. Income figures matching (total, net, taxable)
    6. Tax deducted matching
    7. Date logic (filing date before assessment date)
    8. Installment payments >= $10,000 (flag for review)
    
    Return JSON with:
    {{
      "checks": [
        {{"check": "SIN Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Name Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Address Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Refund Amount Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Total Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Net Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Taxable Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Tax Deducted Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Date Logic", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "High Installment Payment", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}}
      ],
      "overall_risk": "low/medium/high",
      "flagged_items": ["list of concerns"]
    }}
    """.format(t1_data=json.dumps(t1_data), noa_data=json.dumps(noa_data))
    
    try:
        logger.info("Validating cross-document consistency using Gemini")
        
        # Send to Gemini with retry logic
        response = _send_gemini_request(model, prompt, max_retries=3)
        
        # Parse JSON response
        validation_results = _parse_json_response(response)
        
        logger.info(f"Cross-document validation completed with overall risk: {validation_results.get('overall_risk', 'unknown')}")
        return validation_results
        
    except Exception as e:
        logger.error(f"Error in cross-document validation: {str(e)}")
        return {
            "checks": [],
            "overall_risk": "high",
            "flagged_items": [f"Validation error: {str(e)}"]
        }

def validate_accountant_info(accountant_name: str, phone: str, model) -> dict:
    """
    Validate accountant information format
    
    Args:
        accountant_name: Accountant name from T1
        phone: Accountant phone number from T1
        model: Initialized Gemini model
        
    Returns:
        Validation results dictionary
    """
    prompt = """
    Validate this Canadian tax preparer information:
    Name: {accountant_name}
    Phone: {phone}
    
    Check:
    1. Name is not empty/null
    2. Phone number is valid Canadian format (10 digits, various formats accepted)
    3. Any obvious red flags
    
    Return JSON:
    {{
      "name_valid": true/false,
      "phone_valid": true/false,
      "phone_formatted": "standardized format",
      "flags": ["list of issues if any"]
    }}
    """.format(accountant_name=accountant_name or "null", phone=phone or "null")
    
    try:
        logger.info("Validating accountant information using Gemini")
        
        # Send to Gemini with retry logic
        response = _send_gemini_request(model, prompt, max_retries=3)
        
        # Parse JSON response
        validation_results = _parse_json_response(response)
        
        logger.info(f"Accountant validation completed - Name valid: {validation_results.get('name_valid')}, Phone valid: {validation_results.get('phone_valid')}")
        return validation_results
        
    except Exception as e:
        logger.error(f"Error validating accountant info: {str(e)}")
        return {
            "name_valid": False,
            "phone_valid": False,
            "phone_formatted": None,
            "flags": [f"Validation error: {str(e)}"]
        }

def _send_gemini_request(model, prompt: str, max_retries: int = 3) -> str:
    """
    Send request to Gemini API with retry logic and timeout handling
    
    Args:
        model: Initialized Gemini model
        prompt: Prompt to send
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response text from Gemini
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Sending request to Gemini (attempt {attempt + 1}/{max_retries})")
            
            # Generate content with timeout handling
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,  # Consistent extraction
                    max_output_tokens=2048,
                )
            )
            
            if response and response.text:
                logger.info("Successfully received response from Gemini")
                return response.text
            else:
                logger.warning(f"Empty response from Gemini on attempt {attempt + 1}")
                
        except Exception as e:
            logger.error(f"Gemini API error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < max_retries - 1:
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Gemini API failed after {max_retries} attempts: {str(e)}")
    
    raise Exception("Gemini API failed after all retry attempts")

def _parse_json_response(response_text: str) -> dict:
    """
    Parse JSON response from Gemini with error handling
    
    Args:
        response_text: Raw response text from Gemini
        
    Returns:
        Parsed dictionary
    """
    try:
        # Try to find JSON in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx + 1]
            parsed_data = json.loads(json_str)
            logger.info("Successfully parsed JSON response from Gemini")
            return parsed_data
        else:
            logger.warning("No JSON found in Gemini response")
            return {}
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        logger.error(f"Raw response: {response_text[:500]}...")
        return {}
    except Exception as e:
        logger.error(f"Error parsing Gemini response: {str(e)}")
        return {}

def _format_phone_number(phone: str) -> str:
    """
    Format phone number to standard Canadian format
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Formatted phone number
    """
    if not phone:
        return None
    
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone))
    
    # Check if it's a valid Canadian phone number (10 digits)
    if len(digits_only) == 10:
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only[0] == '1':
        # Remove country code
        digits_only = digits_only[1:]
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    else:
        return phone  # Return original if can't format
