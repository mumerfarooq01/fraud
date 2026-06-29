"""
Gemini LLM Validator Module
Modular LLM-based validation using Google Gemini API for Canadian tax documents.
"""

import google.generativeai as genai
import os
import json
import logging
import time
import re
from typing import Dict, Optional, List

from tax_validators.tax_field_schema import (
    T1_EMPTY_FIELDS,
    NOA_EMPTY_FIELDS,
    T1_TEXT_EXTRACTION_INSTRUCTIONS,
    NOA_TEXT_EXTRACTION_INSTRUCTIONS,
    t1_json_schema,
    noa_json_schema,
)
from tax_validators.data_extractor import extract_key_fields
from tax_validators.document_text import MIN_TEXT_LENGTH
from tax_validators.tax_year_extractor import (
    extract_tax_year_from_text,
    extract_tax_year_from_pdf_bytes,
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
        structured_data = _normalize_extraction(
            _parse_json_response(response), T1_EMPTY_FIELDS
        )
        
        logger.info(
            "Successfully extracted %s populated fields from T1",
            _count_populated(structured_data),
        )
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
        structured_data = _normalize_extraction(
            _parse_json_response(response), NOA_EMPTY_FIELDS
        )
        
        logger.info(
            "Successfully extracted %s populated fields from NOA",
            _count_populated(structured_data),
        )
        return structured_data
        
    except Exception as e:
        logger.error(f"Error extracting NOA structured data: {str(e)}")
        return dict(NOA_EMPTY_FIELDS)

MIN_POPULATED_FIELDS = 3
MAX_VISION_PAGES = 5


def extract_structured_data_t1_smart(
    text: str,
    pdf_path: str,
    pdf_bytes: bytes,
    model,
    text_method: str = "unknown",
) -> dict:
    """
    Extract T1 fields using regex bootstrap, Gemini text, and Gemini Vision.
    """
    return _extract_structured_data_smart(
        text=text,
        pdf_path=pdf_path,
        pdf_bytes=pdf_bytes,
        model=model,
        doc_type="t1",
        text_method=text_method,
        empty_template=T1_EMPTY_FIELDS,
        text_extractor=extract_structured_data_t1,
    )


def extract_structured_data_noa_smart(
    text: str,
    pdf_path: str,
    pdf_bytes: bytes,
    model,
    text_method: str = "unknown",
) -> dict:
    """
    Extract NOA fields using regex bootstrap, Gemini text, and Gemini Vision.
    """
    return _extract_structured_data_smart(
        text=text,
        pdf_path=pdf_path,
        pdf_bytes=pdf_bytes,
        model=model,
        doc_type="noa",
        text_method=text_method,
        empty_template=NOA_EMPTY_FIELDS,
        text_extractor=extract_structured_data_noa,
    )


def _extract_structured_data_smart(
    text: str,
    pdf_path: str,
    pdf_bytes: bytes,
    model,
    doc_type: str,
    text_method: str,
    empty_template: dict,
    text_extractor,
) -> dict:
    merged = dict(empty_template)

    # 1) Regex bootstrap from any available text (fast, no API cost)
    if text and text.strip():
        regex_data = _regex_bootstrap_fields(text, doc_type)
        merged = _merge_extraction_results(merged, regex_data, empty_template)
        logger.info(
            "%s regex bootstrap populated %s fields (text_method=%s)",
            doc_type.upper(),
            _count_populated(regex_data),
            text_method,
        )

    use_vision_first = (
        text_method in ("none", "partial", "ocr_partial")
        or not text
        or len(text.strip()) < MIN_TEXT_LENGTH
    )

    # 2) Vision first for scanned/image PDFs
    if use_vision_first:
        logger.info("%s using Gemini Vision first (text_method=%s)", doc_type.upper(), text_method)
        vision_data = _extract_structured_data_from_pdf_vision(
            pdf_path, pdf_bytes, doc_type, model
        )
        merged = _merge_extraction_results(merged, vision_data, empty_template)

    # 3) Gemini text extraction when enough text is available
    if text and len(text.strip()) >= MIN_TEXT_LENGTH and _is_sparse_extraction(merged):
        text_data = text_extractor(text, model)
        merged = _merge_extraction_results(merged, text_data, empty_template)

    # 4) Vision fallback if still sparse
    if _is_sparse_extraction(merged):
        logger.info("%s structured extraction still sparse — trying Gemini Vision", doc_type.upper())
        vision_data = _extract_structured_data_from_pdf_vision(
            pdf_path, pdf_bytes, doc_type, model
        )
        merged = _merge_extraction_results(merged, vision_data, empty_template)

    # 5) Always try dedicated tax year extraction (header OCR + focused vision)
    merged = _enrich_tax_year(merged, text, pdf_bytes, doc_type, model, empty_template)

    logger.info(
        "%s final extraction populated %s/%s fields",
        doc_type.upper(),
        _count_populated(merged),
        len(empty_template),
    )
    return merged


def _regex_bootstrap_fields(text: str, doc_type: str) -> dict:
    """Map regex-based field extraction onto the shared schema."""
    raw = extract_key_fields(text, "T1" if doc_type == "t1" else "NOA")
    mapped = {}

    if raw.get("sin"):
        mapped["sin"] = raw["sin"]
    if raw.get("name"):
        mapped["full_name"] = raw["name"]
    if raw.get("address"):
        mapped["address"] = raw["address"]
    if raw.get("tax_year"):
        mapped["tax_year"] = raw["tax_year"]
    if raw.get("refund_amount"):
        mapped["refund_amount"] = raw["refund_amount"]
    if raw.get("total_income"):
        mapped["total_income"] = raw["total_income"]
    if raw.get("net_income"):
        mapped["net_income"] = raw["net_income"]
    if raw.get("taxable_income"):
        mapped["taxable_income"] = raw["taxable_income"]
    if raw.get("balance_owing"):
        mapped["balance_owing"] = raw["balance_owing"]
    if raw.get("provincial_tax"):
        mapped["provincial_tax"] = raw["provincial_tax"]
    if raw.get("federal_tax"):
        mapped["net_federal_tax"] = raw["federal_tax"]
    if raw.get("accountant_info"):
        mapped["accountant_name"] = raw["accountant_info"]

    if doc_type == "t1" and raw.get("filing_date"):
        mapped["filing_date"] = raw["filing_date"]
    if doc_type == "noa" and raw.get("assessment_date"):
        mapped["date_issued"] = raw["assessment_date"]

    # Dedicated tax year patterns (CRA header labels)
    tax_year = extract_tax_year_from_text(text, doc_type.upper())
    if tax_year:
        mapped["tax_year"] = tax_year

    return mapped


def _enrich_tax_year(
    data: dict,
    text: str,
    pdf_bytes: bytes,
    doc_type: str,
    model,
    template: dict,
) -> dict:
    """Fill tax_year using text patterns, page-1 OCR, then focused Gemini vision."""
    if _has_value(data.get("tax_year")):
        return data

    year = None
    if text and text.strip():
        year = extract_tax_year_from_text(text, doc_type.upper())

    if not year and pdf_bytes:
        year = extract_tax_year_from_pdf_bytes(pdf_bytes, doc_type.upper())

    if not year and pdf_bytes and model:
        year = _extract_tax_year_gemini_vision(pdf_bytes, doc_type, model)

    if year:
        enriched = dict(data)
        enriched["tax_year"] = year
        logger.info("Enriched %s tax_year=%s", doc_type.upper(), year)
        return _normalize_extraction(enriched, template)

    return data


def _extract_tax_year_gemini_vision(
    pdf_bytes: bytes, doc_type: str, model
) -> Optional[str]:
    """Focused single-field Gemini vision call for the taxation year on page 1."""
    prompt = """
    Look at this Canadian tax document (T1 or NOA).
    What is the TAXATION YEAR on the form — the large year in the header (e.g. "2023")?
    This is NOT the filing date or date issued.

    Return ONLY JSON: {"tax_year": "2023"} or {"tax_year": null}
    """
    try:
        from pdf2image import convert_from_bytes
        from tax_validators.tax_year_extractor import _valid_tax_year

        images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=1)
        if not images:
            return None

        response_text = _send_gemini_content_request(model, [prompt, images[0]])
        parsed = _parse_json_response(response_text)
        year = parsed.get("tax_year") if parsed else None
        if _has_value(year):
            return _valid_tax_year(str(year).strip())
    except Exception as exc:
        logger.warning("Focused Gemini tax year extraction failed for %s: %s", doc_type, exc)
    return None


def _count_populated(data: dict) -> int:
    return sum(1 for value in data.values() if _has_value(value))


def _normalize_extraction(data: dict, template: dict) -> dict:
    """Ensure all template keys exist and clean placeholder values."""
    normalized = dict(template)
    if not data:
        return normalized
    for key in template:
        value = data.get(key)
        normalized[key] = value if _has_value(value) else None
    return normalized


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
    """Use Gemini multimodal input (page images, then PDF upload) to extract fields."""
    empty = T1_EMPTY_FIELDS if doc_type == "t1" else NOA_EMPTY_FIELDS
    prompt = _vision_prompt_t1() if doc_type == "t1" else _vision_prompt_noa()

    # 1) Render pages to PIL images — most reliable on App Platform
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, dpi=200)
        if images:
            parts: List = [prompt]
            parts.extend(images[:MAX_VISION_PAGES])
            response_text = _send_gemini_content_request(model, parts)
            parsed = _normalize_extraction(_parse_json_response(response_text), empty)
            if not _is_sparse_extraction(parsed):
                logger.info("Gemini Vision image extraction succeeded for %s", doc_type)
                return parsed
            logger.warning(
                "Gemini Vision image extraction sparse for %s (%s fields)",
                doc_type,
                _count_populated(parsed),
            )
        else:
            logger.warning("pdf2image returned no pages for %s", doc_type)
    except Exception as exc:
        logger.warning("Gemini Vision image extraction failed for %s: %s", doc_type, exc)

    # 2) Fallback: native PDF upload
    try:
        uploaded = genai.upload_file(pdf_path, mime_type="application/pdf")
        uploaded = _wait_for_file_active(uploaded)
        response_text = _send_gemini_content_request(model, [prompt, uploaded])
        _safe_delete_uploaded_file(uploaded)
        parsed = _normalize_extraction(_parse_json_response(response_text), empty)
        logger.info(
            "Gemini Vision PDF upload extracted %s fields for %s",
            _count_populated(parsed),
            doc_type,
        )
        return parsed
    except Exception as exc:
        logger.warning("Gemini Vision PDF upload failed for %s: %s", doc_type, exc)
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
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            response_text = _get_response_text(response)
            if response_text:
                return response_text
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
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                )
            )
            
            response_text = _get_response_text(response)
            if response_text:
                logger.info("Successfully received response from Gemini")
                return response_text
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

def _get_response_text(response) -> str:
    """Extract text from a Gemini response, including blocked/partial candidates."""
    if not response:
        return ""

    try:
        text = response.text
        if text and text.strip():
            return text.strip()
    except (ValueError, AttributeError):
        pass

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        chunks = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(part_text)
        if chunks:
            return "".join(chunks).strip()

    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback:
        logger.warning("Gemini prompt feedback: %s", prompt_feedback)

    return ""


def _parse_json_response(response_text: str) -> dict:
    """
    Parse JSON response from Gemini with error handling
    
    Args:
        response_text: Raw response text from Gemini
        
    Returns:
        Parsed dictionary
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty Gemini response text")
        return {}

    try:
        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        # Try direct parse first
        try:
            parsed_data = json.loads(text)
            logger.info("Successfully parsed JSON response from Gemini")
            return parsed_data if isinstance(parsed_data, dict) else {}
        except json.JSONDecodeError:
            pass

        # Fallback: extract outermost JSON object
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx + 1]
            parsed_data = json.loads(json_str)
            logger.info("Successfully parsed embedded JSON response from Gemini")
            return parsed_data if isinstance(parsed_data, dict) else {}

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
