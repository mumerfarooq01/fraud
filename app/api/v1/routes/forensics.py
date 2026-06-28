from forensics.visualizer_api import create_forensic_visualizations_api
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from app.api.v1.schemas.forensics import ForensicAnalysisResponse, ErrorResponse
from app.config import settings
import time
import tempfile
import os
import traceback

# Import existing forensics module
analyze_document_forensics = None
try:
    from forensics import analyze_document_forensics
    from forensics.forensic_analyzer import preprocess_uploaded_file
    print("[SUCCESS] Forensics module imported successfully")
except ImportError as e:
    print(f"[ERROR] Could not import forensics module: {e}")
    traceback.print_exc()  # Fixed: proper way to print traceback
except Exception as e:
    print(f"[ERROR] Exception during forensics import: {e}")
    traceback.print_exc()

router = APIRouter()


@router.post(
    "/forensics/analyze",
    response_model=ForensicAnalysisResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Analyze document for forensic indicators",
    description="""
    Upload a document (PDF, JPEG, or PNG) for comprehensive forensic analysis.
    
    The analysis includes:
    - Text alignment consistency
    - Font usage patterns
    - PDF metadata examination
    - Number formatting patterns
    - Image quality assessment
    - Page numbering (NOA documents)
    - ID duplicate detection (NOA documents)
    """
)
async def analyze_document(
    file: UploadFile = File(..., description="Document to analyze"),
    doc_type: str = Query(
        default="unknown",
        description="Document type: 'noa', 't1', or 'unknown'",
        regex="^(noa|t1|unknown)$"
    )
):
    """
    Perform comprehensive forensic analysis on uploaded document
    """
    
    # Check if forensics module is available
    if analyze_document_forensics is None:
        raise HTTPException(
            status_code=503,
            detail="Forensics analysis module is not available. Please check server logs."
        )
    
    start_time = time.time()
    
    # Validate file extension
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    if len(file_content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        # Run forensic analysis
        results = analyze_document_forensics(
            pdf_file=tmp_path,
            pdf_bytes=file_content,
            file_name=file.filename,
            doc_type=doc_type.lower()
        )
    
        # Generate visual forensics
        try:
            visualizations = create_forensic_visualizations_api(
                pdf_file=tmp_path,
                pdf_bytes=file_content,
                forensic_results=results,
                max_pages=2  # Limit to first 2 pages for performance
            )
        except Exception as viz_error:
            print(f"[WARNING] Could not generate visualizations: {viz_error}")
            visualizations = None
    
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Build response
        response_data = {
            **results,
            "processing_time": processing_time,
            "file_name": file.filename,
            "doc_type": doc_type,
            "visualizations": visualizations  # Add visualizations
        }
        
        # Handle missing keys gracefully
        for key in ['alignment', 'fonts', 'metadata', 'numbers', 'image']:
            if key not in response_data:
                response_data[key] = {
                    'risk_score': 0,
                    'applicable': False,
                    'error': f'{key} check not available'
                }
        
        return ForensicAnalysisResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Forensic analysis failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass

@router.get(
    "/forensics/supported-formats",
    summary="Get supported file formats",
    description="Returns list of supported file formats and size limits"
)
async def get_supported_formats():
    """Get supported file formats and upload limits"""
    return {
        "formats": settings.ALLOWED_EXTENSIONS,
        "max_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_size_bytes": settings.max_file_size_bytes
    }

@router.get(
    "/forensics/checks",
    summary="Get list of forensic checks",
    description="Returns information about all available forensic checks"
)
async def get_available_checks():
    """Get list of all forensic checks performed"""
    return {
        "checks": [
            {
                "name": "alignment",
                "description": "Detects misaligned text rows",
                "applicable_to": ["all"]
            },
            {
                "name": "fonts",
                "description": "Analyzes font consistency",
                "applicable_to": ["all"]
            },
            {
                "name": "metadata",
                "description": "Examines PDF metadata for suspicious signs",
                "applicable_to": ["pdf"]
            },
            {
                "name": "numbers",
                "description": "Checks number formatting consistency",
                "applicable_to": ["all"]
            },
            {
                "name": "image",
                "description": "Analyzes image quality and blur",
                "applicable_to": ["all"]
            },
            {
                "name": "page_numbers",
                "description": "Verifies page numbering sequence",
                "applicable_to": ["noa"]
            },
            {
                "name": "noa_id_check",
                "description": "Detects duplicate NOA identification numbers",
                "applicable_to": ["noa"]
            }
        ]
    }




