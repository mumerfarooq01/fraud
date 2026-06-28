from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ValidationCheck(BaseModel):
    """Single validation check result"""
    check: str = Field(description="Name of the check")
    status: str = Field(description="Status: pass, fail, or warning")
    confidence: int = Field(ge=0, le=100, description="Confidence level")
    details: str = Field(description="Detailed explanation")

class ComparisonResponse(BaseModel):
    """T1 vs NOA comparison results"""
    overall_risk: str = Field(description="Overall risk: low, medium, or high")
    checks: List[ValidationCheck] = Field(description="List of validation checks performed")
    flagged_items: List[str] = Field(description="Items flagged for review")
    
    # Extracted data
    t1_data: Dict[str, Any] = Field(description="Data extracted from T1")
    noa_data: Dict[str, Any] = Field(description="Data extracted from NOA")
    
    # Metadata
    processing_time: float = Field(description="Processing time in seconds")




