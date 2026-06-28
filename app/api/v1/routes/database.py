from fastapi import APIRouter, HTTPException, Query, Path
from app.api.v1.schemas.forensics import ForensicRecordResponse, DuplicateDetectionResponse
from typing import List

# Import forensic database
try:
    from forensics.database import ForensicDatabase
except ImportError as e:
    print(f"[WARNING] Could not import forensic database: {e}")

router = APIRouter()

@router.get(
    "/forensics/records",
    response_model=List[ForensicRecordResponse],
    summary="Get all forensic records",
    description="Retrieve stored NOA identification records with pagination"
)
async def get_forensic_records(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get all forensic database records
    """
    try:
        db = ForensicDatabase()
        records = db.get_all_records()
        
        # Paginate
        paginated_records = records[offset:offset + limit]
        
        # Convert to response models
        response = []
        for record in paginated_records:
            response.append(ForensicRecordResponse(
                id=record[0],
                identification_number=record[1],
                sin_last_4=record[2],
                full_name=record[3],
                date_issued=record[4],
                uploaded_timestamp=record[5],
                file_name=record[7] if len(record) > 7 else "Unknown"
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/forensics/duplicates",
    response_model=List[DuplicateDetectionResponse],
    summary="Get duplicate detection history",
    description="Retrieve all duplicate ID detections"
)
async def get_duplicate_detections():
    """
    Get all duplicate ID detections
    """
    try:
        db = ForensicDatabase()
        duplicates = db.get_duplicate_history()
        
        response = []
        for dup in duplicates:
            response.append(DuplicateDetectionResponse(
                id=dup[0],
                identification_number=dup[1],
                original_file_name=dup[5] if len(dup) > 5 else "Unknown",
                duplicate_file_name=dup[3],
                detected_timestamp=dup[4]
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/forensics/check-duplicate/{id_number}",
    summary="Check if ID is duplicate",
    description="Check if a specific NOA identification number has been seen before"
)
async def check_duplicate_id(
    id_number: str = Path(..., description="NOA identification number to check")
):
    """
    Check if ID number exists in database
    """
    try:
        db = ForensicDatabase()
        result = db.check_duplicate_id(id_number)
        
        return {
            "id_number": id_number,
            "is_duplicate": result['is_duplicate'],
            "original_record": result.get('original_record')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/forensics/stats",
    summary="Get database statistics",
    description="Get statistics about the forensic database"
)
async def get_database_stats():
    """
    Get forensic database statistics
    """
    try:
        db = ForensicDatabase()
        records = db.get_all_records()
        duplicates = db.get_duplicate_history()
        
        return {
            "total_records": len(records),
            "total_duplicates_detected": len(duplicates),
            "duplicate_rate_percent": (len(duplicates) / len(records) * 100) if records else 0,
            "database_path": db.db_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




