from pydantic import BaseModel, Field
from typing import Dict, Any, List


class DocumentExtractionResponse(BaseModel):
    """Structured fields extracted from a single tax document."""

    doc_type: str = Field(description="Document type: t1 or noa")
    data: Dict[str, Any] = Field(description="Extracted field values")
    fields_populated: int = Field(description="Number of non-null fields extracted")
    fields_total: int = Field(description="Total fields in schema")
    text_method: str = Field(description="How PDF text was obtained")
    extraction_methods: List[str] = Field(description="Pipeline steps used")
    processing_time: float = Field(description="Processing time in seconds")
