"""
Deep phased field extraction for T1 and NOA documents.
Runs separate focused Gemini calls per field group for better accuracy on scanned PDFs.
"""

import logging
import time
from typing import Dict, List, Tuple

from tax_validators.tax_field_schema import (
    T1_EMPTY_FIELDS,
    NOA_EMPTY_FIELDS,
    T1_FIELD_NAMES,
    NOA_FIELD_NAMES,
    _null_schema,
)
from tax_validators.document_text import extract_document_text
from tax_validators.gemini_validator import (
    initialize_gemini,
    extract_structured_data_t1_smart,
    extract_structured_data_noa_smart,
    _merge_extraction_results,
    _send_gemini_content_request,
    _send_gemini_request,
    _parse_json_response,
    _normalize_extraction,
    _count_populated,
    _enrich_tax_year,
    MAX_VISION_PAGES,
)

logger = logging.getLogger(__name__)

T1_EXTRACTION_GROUPS = [
    {
        "name": "identity",
        "fields": [
            "sin",
            "full_name",
            "address",
            "province",
            "marital_status",
            "tax_year",
            "filing_date",
        ],
        "instruction": """
        From this Canadian T1 Income Tax Return extract IDENTITY fields only:
        - sin: Social Insurance Number
        - full_name: taxpayer name
        - address: complete address
        - province: province of residence
        - marital_status: marital status on the return
        - tax_year: taxation year in the form header (e.g. 2023), NOT the filing date year
        - filing_date: date the return was signed or filed
        """,
    },
    {
        "name": "income",
        "fields": [
            "total_income",
            "employment_income",
            "self_employment_income",
            "dividend_income",
            "capital_gains",
            "net_income",
            "taxable_income",
        ],
        "instruction": """
        From this Canadian T1 extract INCOME amounts only (Line numbers if visible):
        - total_income (Line 150)
        - employment_income
        - self_employment_income
        - dividend_income
        - capital_gains
        - net_income (Line 236)
        - taxable_income (Line 260)
        Return dollar amounts as numbers or strings without currency symbols.
        """,
    },
    {
        "name": "tax_and_deductions",
        "fields": [
            "refund_amount",
            "balance_owing",
            "tax_deducted",
            "tax_paid_instalments",
            "net_federal_tax",
            "provincial_tax",
            "cpp_contributions",
            "ei_premiums",
            "rrsp_deduction",
        ],
        "instruction": """
        From this Canadian T1 extract TAX and DEDUCTION amounts only:
        - refund_amount or balance_owing (whichever applies)
        - tax_deducted, tax_paid_instalments
        - net_federal_tax, provincial_tax
        - cpp_contributions, ei_premiums, rrsp_deduction
        """,
    },
    {
        "name": "preparer",
        "fields": [
            "accountant_name",
            "accountant_phone",
            "tax_preparer_efile_number",
        ],
        "instruction": """
        From this Canadian T1 extract TAX PREPARER information if present:
        - accountant_name (preparer/firm name)
        - accountant_phone (digits only if possible)
        - tax_preparer_efile_number (EFILE or preparer ID)
        """,
    },
]

NOA_EXTRACTION_GROUPS = [
    {
        "name": "identity",
        "fields": [
            "sin",
            "full_name",
            "address",
            "province",
            "tax_year",
            "date_issued",
            "noa_identification_number",
            "assessment_result",
        ],
        "instruction": """
        From this Canadian Notice of Assessment (NOA) extract IDENTITY and header fields:
        - sin (may be partially masked)
        - full_name, address, province
        - tax_year: taxation year assessed (NOT date issued year)
        - date_issued: notice/assessment date
        - noa_identification_number: NOA ID at top of document
        - assessment_result: refund, balance owing, or nil
        """,
    },
    {
        "name": "amounts",
        "fields": [
            "refund_amount",
            "balance_owing",
            "account_balance",
            "total_income",
            "employment_income",
            "self_employment_income",
            "net_income",
            "taxable_income",
            "tax_deducted",
            "tax_paid_instalments",
            "net_federal_tax",
            "provincial_tax",
        ],
        "instruction": """
        From this Canadian NOA extract all dollar amounts shown in the assessment summary:
        refund, balance owing, account balance, income lines, tax deducted, instalments,
        net federal tax, provincial tax.
        """,
    },
    {
        "name": "credits",
        "fields": [
            "rrsp_deduction_limit",
            "home_buyers_plan_balance",
            "tuition_credits",
        ],
        "instruction": """
        From this Canadian NOA extract limits and credits if shown:
        RRSP deduction limit, Home Buyers' Plan balance, tuition credits.
        """,
    },
]


def extract_t1_document_deep(
    pdf_path: str, pdf_bytes: bytes, model=None
) -> Tuple[dict, dict]:
    """
    Deep T1 extraction using phased vision + smart pipeline.

    Returns:
        (data dict, metadata dict)
    """
    return _extract_document_deep(
        pdf_path=pdf_path,
        pdf_bytes=pdf_bytes,
        doc_type="t1",
        empty_template=T1_EMPTY_FIELDS,
        groups=T1_EXTRACTION_GROUPS,
        smart_extractor=extract_structured_data_t1_smart,
        model=model,
    )


def extract_noa_document_deep(
    pdf_path: str, pdf_bytes: bytes, model=None
) -> Tuple[dict, dict]:
    """
    Deep NOA extraction using phased vision + smart pipeline.

    Returns:
        (data dict, metadata dict)
    """
    return _extract_document_deep(
        pdf_path=pdf_path,
        pdf_bytes=pdf_bytes,
        doc_type="noa",
        empty_template=NOA_EMPTY_FIELDS,
        groups=NOA_EXTRACTION_GROUPS,
        smart_extractor=extract_structured_data_noa_smart,
        model=model,
    )


def _extract_document_deep(
    pdf_path: str,
    pdf_bytes: bytes,
    doc_type: str,
    empty_template: dict,
    groups: List[dict],
    smart_extractor,
    model=None,
) -> Tuple[dict, dict]:
    start = time.time()
    methods: List[str] = []

    if model is None:
        model = initialize_gemini()

    text, text_method = extract_document_text(pdf_path, pdf_bytes)
    methods.append(f"text:{text_method}")

    merged = dict(empty_template)

    # Phased vision extraction — one focused call per field group
    for group in groups:
        group_data = _extract_field_group(
            pdf_bytes=pdf_bytes,
            text=text,
            model=model,
            group=group,
            doc_type=doc_type,
        )
        if _count_populated(group_data) > 0:
            methods.append(f"vision:{group['name']}")
        merged = _merge_extraction_results(merged, group_data, empty_template)

    # Full smart pipeline merge (regex + vision + text)
    smart_data = smart_extractor(text, pdf_path, pdf_bytes, model, text_method=text_method)
    if _count_populated(smart_data) > 0:
        methods.append("smart_pipeline")
    merged = _merge_extraction_results(merged, smart_data, empty_template)

    merged = _enrich_tax_year(merged, text, pdf_bytes, doc_type, model, empty_template)

    metadata = {
        "doc_type": doc_type,
        "text_method": text_method,
        "extraction_methods": methods,
        "fields_populated": _count_populated(merged),
        "fields_total": len(empty_template),
        "processing_time": round(time.time() - start, 2),
    }

    logger.info(
        "%s deep extraction: %s/%s fields via %s",
        doc_type.upper(),
        metadata["fields_populated"],
        metadata["fields_total"],
        methods,
    )

    return merged, metadata


def _extract_field_group(
    pdf_bytes: bytes,
    text: str,
    model,
    group: dict,
    doc_type: str,
) -> dict:
    """Extract one field group via vision (images) then text fallback."""
    fields = group["fields"]
    schema = _null_schema(fields)
    prompt = f"""
    You are reading a Canadian {'T1 Income Tax Return' if doc_type == 't1' else 'Notice of Assessment'}.
    {group['instruction']}

    Return ONLY JSON with these EXACT keys:
    {schema}
    Use null for missing fields. No markdown.
    """

    data = {}

    # Vision: page images
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, dpi=200)
        if images:
            parts: List = [prompt]
            parts.extend(images[:MAX_VISION_PAGES])
            response_text = _send_gemini_content_request(model, parts)
            data = _normalize_extraction(
                _parse_json_response(response_text),
                {f: None for f in fields},
            )
    except Exception as exc:
        logger.warning("Vision group %s failed for %s: %s", group["name"], doc_type, exc)

    # Text fallback for this group if vision sparse
    if _count_populated(data) < 2 and text and len(text.strip()) > 100:
        try:
            text_prompt = f"""{prompt}

            Document text:
            {text[:12000]}
            """
            response_text = _send_gemini_request(model, text_prompt, max_retries=2)
            text_data = _normalize_extraction(
                _parse_json_response(response_text),
                {f: None for f in fields},
            )
            data = _merge_extraction_results(data, text_data, {f: None for f in fields})
        except Exception as exc:
            logger.warning("Text group %s failed for %s: %s", group["name"], doc_type, exc)

    return data
