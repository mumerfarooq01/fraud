from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Response Models
class CheckResult(BaseModel):
    """Result from a single forensic check"""
    risk_score: int = Field(ge=0, le=100, description="Risk score from 0 (safe) to 100 (high risk)")
    applicable: bool = Field(default=True, description="Whether this check applies to the document")
    issues: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of issues found")
    flags: Optional[List[str]] = Field(default=None, description="Warning flags")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
    error: Optional[str] = Field(default=None, description="Error message if check failed")

class ForensicAnalysisResponse(BaseModel):
    """Response model for forensic analysis"""
    file_name: str
    doc_type: str
    processing_time: float
    
    # Forensic check results
    alignment: Dict[str, Any]
    fonts: Dict[str, Any]
    metadata: Dict[str, Any]
    numbers: Dict[str, Any]
    image: Dict[str, Any]
    page_numbers: Optional[Dict[str, Any]] = None
    noa_id_check: Optional[Dict[str, Any]] = None
    
    # NEW: Visual forensics
    visualizations: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Base64-encoded visualization images showing forensic issues"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "document.pdf",
                "doc_type": "noa",
                "processing_time": 2.45,
                "alignment": {"risk_score": 30, "applicable": True},
                "fonts": {"risk_score": 45, "applicable": True},
                "visualizations": [
                    {
                        "page": 1,
                        "image_base64": "iVBORw0KGgoAAAANS...",
                        "format": "png"
                    }
                ]
            }
        }

class ForensicRecordResponse(BaseModel):
    """Forensic database record"""
    id: int
    identification_number: str
    sin_last_4: Optional[str] = None
    full_name: Optional[str] = None
    date_issued: Optional[str] = None
    uploaded_timestamp: str
    file_name: str

class DuplicateDetectionResponse(BaseModel):
    """Duplicate ID detection record"""
    id: int
    identification_number: str
    original_file_name: str
    duplicate_file_name: str
    detected_timestamp: str

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: str
    type: Optional[str] = None




