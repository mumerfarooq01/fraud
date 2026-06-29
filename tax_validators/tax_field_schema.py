"""
Shared field definitions for Canadian T1 and NOA document extraction.
"""

from typing import Dict, List


def _null_schema(fields: List[str]) -> str:
    lines = [f'      "{field}": "value or null",' for field in fields]
    return "{\n" + "\n".join(lines).rstrip(",") + "\n    }"


T1_FIELD_NAMES: List[str] = [
    "sin",
    "full_name",
    "address",
    "tax_year",
    "province",
    "marital_status",
    "refund_amount",
    "balance_owing",
    "total_income",
    "employment_income",
    "self_employment_income",
    "net_income",
    "taxable_income",
    "tax_deducted",
    "tax_paid_instalments",
    "net_federal_tax",
    "provincial_tax",
    "cpp_contributions",
    "ei_premiums",
    "rrsp_deduction",
    "dividend_income",
    "capital_gains",
    "accountant_name",
    "accountant_phone",
    "tax_preparer_efile_number",
    "filing_date",
]

NOA_FIELD_NAMES: List[str] = [
    "sin",
    "full_name",
    "address",
    "tax_year",
    "province",
    "noa_identification_number",
    "date_issued",
    "assessment_result",
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
    "rrsp_deduction_limit",
    "home_buyers_plan_balance",
    "tuition_credits",
]

T1_EMPTY_FIELDS: Dict[str, None] = {field: None for field in T1_FIELD_NAMES}
NOA_EMPTY_FIELDS: Dict[str, None] = {field: None for field in NOA_FIELD_NAMES}

T1_TEXT_EXTRACTION_INSTRUCTIONS = """
    Extract the following from this Canadian T1 Income Tax Return:
    - Identity: SIN, full name, address, province, marital status
    - tax_year: THE TAXATION YEAR on the form (large year in header, e.g. "2023").
      This is NOT the filing date year. Look for "Tax year", "For the 2023 taxation year",
      or the prominent year at the top of page 1.
    - filing_date: date the return was signed/filed
    - Income: total, employment, self-employment, dividends, capital gains, net, taxable
    - Tax amounts: refund, balance owing, tax deducted, instalments, net federal tax, provincial tax
    - Deductions/contributions: CPP, EI, RRSP
    - Preparer: accountant name, phone, EFILE/preparer number if shown
    """

NOA_TEXT_EXTRACTION_INSTRUCTIONS = """
    Extract the following from this Canadian Notice of Assessment (NOA):
    - Identity: SIN (may be partially masked), full name, address, province
    - tax_year: THE TAXATION YEAR being assessed (labeled "Tax year" on the NOA, e.g. "2023").
      NOT the "Date issued" year unless no tax year label exists.
    - NOA identification number, date_issued (assessment notice date)
    - Assessment outcome: refund, balance owing, or nil (assessment_result)
    - Account balance/refund as shown on the NOA
    - Income: total, employment, self-employment, net, taxable
    - Tax: deducted, instalments, net federal tax, provincial tax
    - Limits/credits: RRSP deduction limit, Home Buyers' Plan balance, tuition credits if shown
    """


def t1_json_schema() -> str:
    return _null_schema(T1_FIELD_NAMES)


def noa_json_schema() -> str:
    return _null_schema(NOA_FIELD_NAMES)
