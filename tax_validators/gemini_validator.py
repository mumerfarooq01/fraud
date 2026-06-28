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

from tax_validators.tax_field_schema import (
    T1_EMPTY_FIELDS,
    NOA_EMPTY_FIELDS,
    T1_TEXT_EXTRACTION_INSTRUCTIONS,
    NOA_TEXT_EXTRACTION_INSTRUCTIONS,
    t1_json_schema,
    noa_json_schema,
)

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
    prompt = f"""
    {T1_TEXT_EXTRACTION_INSTRUCTIONS}

    Return ONLY a JSON object with these EXACT field names:
    {t1_json_schema()}

    Use null for missing fields. Return ONLY the JSON, no other text.

    Document text:
    {text}
    """
    
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
        return dict(T1_EMPTY_FIELDS)


def extract_structured_data_noa(text: str, model) -> dict:
    """
    Use Gemini to extract structured data from NOA document
    
    Args:
        text: Extracted text from NOA document
        model: Initialized Gemini model
        
    Returns:
        Structured dictionary with extracted data
    """
    prompt = f"""
    {NOA_TEXT_EXTRACTION_INSTRUCTIONS}

    Return ONLY a JSON object with these EXACT field names:
    {noa_json_schema()}

    Use null for missing fields. Return ONLY the JSON, no other text.

    Document text:
    {text}
    """
    
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
        return dict(NOA_EMPTY_FIELDS)

MIN_POPULATED_FIELDS = 3
MAX_VISION_PAGES = 5


def extract_structured_data_t1_smart(
    text: str, pdf_path: str, pdf_bytes: bytes, model
) -> dict:
    """
    Extract T1 fields from text, then fall back to Gemini Vision on the PDF if sparse.
    """
    data = (
        extract_structured_data_t1(text, model)
        if text and text.strip()
        else dict(T1_EMPTY_FIELDS)
    )

    if not _is_sparse_extraction(data):
        return data

    logger.info("T1 structured extraction sparse — falling back to Gemini Vision")
    vision_data = _extract_structured_data_from_pdf_vision(
        pdf_path, pdf_bytes, "t1", model
    )
    return _merge_extraction_results(data, vision_data, T1_EMPTY_FIELDS)


def extract_structured_data_noa_smart(
    text: str, pdf_path: str, pdf_bytes: bytes, model
) -> dict:
    """
    Extract NOA fields from text, then fall back to Gemini Vision on the PDF if sparse.
    """
    data = (
        extract_structured_data_noa(text, model)
        if text and text.strip()
        else dict(NOA_EMPTY_FIELDS)
    )

    if not _is_sparse_extraction(data):
        return data

    logger.info("NOA structured extraction sparse — falling back to Gemini Vision")
    vision_data = _extract_structured_data_from_pdf_vision(
        pdf_path, pdf_bytes, "noa", model
    )
    return _merge_extraction_results(data, vision_data, NOA_EMPTY_FIELDS)


def _is_sparse_extraction(data: dict) -> bool:
    """True when too few fields were extracted to be useful."""
    if not data:
        return True
    populated = sum(
        1
        for value in data.values()
        if value is not None and str(value).strip().lower() not in ("", "null", "none", "n/a")
    )
    return populated < MIN_POPULATED_FIELDS


def _merge_extraction_results(primary: dict, fallback: dict, template: dict) -> dict:
    """Prefer primary values, fill gaps from fallback/vision."""
    merged = dict(template)
    for key in template:
        primary_val = primary.get(key) if primary else None
        fallback_val = fallback.get(key) if fallback else None
        if _has_value(primary_val):
            merged[key] = primary_val
        elif _has_value(fallback_val):
            merged[key] = fallback_val
        else:
            merged[key] = None
    return merged


def _has_value(value) -> bool:
    return value is not None and str(value).strip().lower() not in ("", "null", "none", "n/a")


def _vision_prompt_t1() -> str:
    return f"""
    You are reading a Canadian T1 Income Tax Return PDF document (image or file).
    {T1_TEXT_EXTRACTION_INSTRUCTIONS}
    Return ONLY a JSON object with these EXACT keys:
    {t1_json_schema()}
    Use null for missing fields. Return ONLY valid JSON, no markdown.
    """


def _vision_prompt_noa() -> str:
    return f"""
    You are reading a Canadian Notice of Assessment (NOA) PDF document (image or file).
    {NOA_TEXT_EXTRACTION_INSTRUCTIONS}
    Return ONLY a JSON object with these EXACT keys:
    {noa_json_schema()}
    Use null for missing fields. Return ONLY valid JSON, no markdown.
    """


def _extract_structured_data_from_pdf_vision(
    pdf_path: str, pdf_bytes: bytes, doc_type: str, model
) -> dict:
    """Use Gemini multimodal input (PDF upload, then page images) to extract fields."""
    empty = T1_EMPTY_FIELDS if doc_type == "t1" else NOA_EMPTY_FIELDS
    prompt = _vision_prompt_t1() if doc_type == "t1" else _vision_prompt_noa()

    # 1) Try native PDF upload
    try:
        uploaded = genai.upload_file(pdf_path, mime_type="application/pdf")
        uploaded = _wait_for_file_active(uploaded)
        response_text = _send_gemini_content_request(model, [prompt, uploaded])
        _safe_delete_uploaded_file(uploaded)
        parsed = _parse_json_response(response_text)
        if not _is_sparse_extraction(parsed):
            logger.info("Gemini Vision PDF upload succeeded for %s", doc_type)
            return parsed
        logger.warning("Gemini Vision PDF upload returned sparse data for %s", doc_type)
    except Exception as exc:
        logger.warning("Gemini Vision PDF upload failed for %s: %s", doc_type, exc)

    # 2) Fallback: send rendered page images
    try:
        from pdf2image import convert_from_bytes
        import io

        images = convert_from_bytes(pdf_bytes, dpi=200)
        parts = [prompt]
        for image in images[:MAX_VISION_PAGES]:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            parts.append({"mime_type": "image/png", "data": buffer.getvalue()})

        response_text = _send_gemini_content_request(model, parts)
        parsed = _parse_json_response(response_text)
        logger.info(
            "Gemini Vision image fallback extracted %s fields for %s",
            sum(1 for v in parsed.values() if _has_value(v)),
            doc_type,
        )
        return parsed if parsed else dict(empty)
    except Exception as exc:
        logger.error("Gemini Vision image fallback failed for %s: %s", doc_type, exc)
        return dict(empty)


def _wait_for_file_active(uploaded, timeout_seconds: int = 90):
    """Wait until an uploaded Gemini file is ready."""
    deadline = time.time() + timeout_seconds
    current = uploaded
    while current.state.name == "PROCESSING":
        if time.time() > deadline:
            raise TimeoutError("Gemini file processing timed out")
        time.sleep(2)
        current = genai.get_file(current.name)
    if current.state.name != "ACTIVE":
        raise ValueError(f"Uploaded file not active: {current.state.name}")
    return current


def _safe_delete_uploaded_file(uploaded) -> None:
    try:
        if uploaded and getattr(uploaded, "name", None):
            genai.delete_file(uploaded.name)
    except Exception as exc:
        logger.debug("Could not delete uploaded Gemini file: %s", exc)


def _send_gemini_content_request(model, parts, max_retries: int = 3) -> str:
    """Send multimodal content (text, files, images) to Gemini."""
    for attempt in range(max_retries):
        try:
            logger.info(
                "Sending multimodal request to Gemini (attempt %s/%s)",
                attempt + 1,
                max_retries,
            )
            response = model.generate_content(
                parts,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=4096,
                ),
            )
            if response and response.text:
                return response.text
            logger.warning("Empty multimodal response from Gemini on attempt %s", attempt + 1)
        except Exception as exc:
            logger.error("Gemini multimodal error on attempt %s: %s", attempt + 1, exc)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    raise Exception("Gemini multimodal request failed after all retry attempts")


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
    3. Address and province matching
    4. Tax year matching between T1 and NOA
    5. Refund amount OR balance owing consistency (T1 refund vs NOA refund/balance)
    6. Income figures matching (total, employment, self-employment, net, taxable)
    7. Tax deducted, instalments, net federal tax, and provincial tax matching
    8. CPP, EI, RRSP figures on T1 vs NOA limits/credits where comparable
    9. Date logic (filing date before assessment date)
    10. NOA identification number present on NOA
    11. Installment payments >= $10,000 (flag for review)
    12. Assessment result (refund/balance/nil) consistent with dollar amounts
    
    Return JSON with:
    {{
      "checks": [
        {{"check": "SIN Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Name Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Address Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Province Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Tax Year Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Refund/Balance Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Total Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Employment Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Net Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Taxable Income Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Tax Deducted Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Net Federal Tax Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Provincial Tax Match", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "Date Logic", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
        {{"check": "NOA ID Present", "status": "pass/fail/warning", "confidence": 0-100, "details": "explanation"}},
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
                    max_output_tokens=4096,
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
