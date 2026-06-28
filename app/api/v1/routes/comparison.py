from fastapi import APIRouter, UploadFile, File, HTTPException
from app.api.v1.schemas.comparison import ComparisonResponse
from app.config import settings
import time
import tempfile
import os

# Import existing validators
try:
    from tax_validators.data_extractor import extract_text_from_pdf
    from tax_validators.gemini_validator import (
        initialize_gemini,
        extract_structured_data_t1,
        extract_structured_data_noa,
        validate_cross_document
    )
except ImportError as e:
    print(f"[WARNING] Could not import validators: {e}")

router = APIRouter()

@router.post(
    "/comparison/validate",
    response_model=ComparisonResponse,
    summary="Compare T1 and NOA documents",
    description="""
    Upload T1 Income Tax Return and Notice of Assessment for cross-document validation.
    
    Checks include:
    - SIN matching
    - Name and address consistency
    - Refund amount matching
    - Income figures matching
    - Date logic validation
    - Accountant information
    """
)
async def validate_documents(
    t1_file: UploadFile = File(..., description="T1 Income Tax Return (PDF)"),
    noa_file: UploadFile = File(..., description="Notice of Assessment (PDF)")
):
    """
    Validate consistency between T1 and NOA documents
    """
    
    start_time = time.time()
    
    # Validate file types
    if not t1_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="T1 file must be PDF format")
    
    if not noa_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="NOA file must be PDF format")
    
    # Read file contents
    t1_content = await t1_file.read()
    noa_content = await noa_file.read()
    
    # Validate file sizes
    if len(t1_content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=400, detail=f"T1 file too large (max {settings.MAX_FILE_SIZE_MB}MB)")
    
    if len(noa_content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=400, detail=f"NOA file too large (max {settings.MAX_FILE_SIZE_MB}MB)")
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as t1_tmp:
        t1_tmp.write(t1_content)
        t1_path = t1_tmp.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as noa_tmp:
        noa_tmp.write(noa_content)
        noa_path = noa_tmp.name
    
    try:
        # Check if Gemini is configured
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Gemini API key not configured. Document comparison requires AI analysis."
            )
        
        # Initialize Gemini
        model = initialize_gemini()
        
        # Extract text from both documents
        t1_text = extract_text_from_pdf(t1_path)
        noa_text = extract_text_from_pdf(noa_path)
        
        # Extract structured data
        t1_data = extract_structured_data_t1(t1_text, model)
        noa_data = extract_structured_data_noa(noa_text, model)
        
        # Perform cross-document validation
        validation_results = validate_cross_document(t1_data, noa_data, model)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Build response
        response = ComparisonResponse(
            overall_risk=validation_results.get('overall_risk', 'unknown'),
            checks=validation_results.get('checks', []),
            flagged_items=validation_results.get('flagged_items', []),
            t1_data=t1_data,
            noa_data=noa_data,
            processing_time=processing_time
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document comparison failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary files
        for path in [t1_path, noa_path]:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass




