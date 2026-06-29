from fastapi import APIRouter, UploadFile, File, HTTPException
from app.api.v1.schemas.documents import DocumentExtractionResponse
from app.config import settings
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    from tax_validators.document_field_extractor import (
        extract_t1_document_deep,
        extract_noa_document_deep,
    )
    from tax_validators.tax_field_schema import T1_FIELD_NAMES, NOA_FIELD_NAMES
except ImportError as e:
    print(f"[WARNING] Could not import document extractors: {e}")

router = APIRouter()


async def _read_pdf(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    content = await upload.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    return content


def _run_extraction(content: bytes, doc_type: str) -> DocumentExtractionResponse:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key not configured.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        pdf_path = tmp.name

    try:
        if doc_type == "t1":
            data, meta = extract_t1_document_deep(pdf_path, content)
            fields_total = len(T1_FIELD_NAMES)
        else:
            data, meta = extract_noa_document_deep(pdf_path, content)
            fields_total = len(NOA_FIELD_NAMES)

        return DocumentExtractionResponse(
            doc_type=doc_type,
            data=data,
            fields_populated=meta["fields_populated"],
            fields_total=fields_total,
            text_method=meta["text_method"],
            extraction_methods=meta["extraction_methods"],
            processing_time=meta["processing_time"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Document extraction failed for %s", doc_type)
        raise HTTPException(
            status_code=500,
            detail=f"{doc_type.upper()} extraction failed: {str(exc)}",
        ) from exc
    finally:
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except OSError:
            pass


@router.post(
    "/documents/extract/t1",
    response_model=DocumentExtractionResponse,
    summary="Deep extract T1 Income Tax Return fields",
    description="""
    Dedicated extraction pass for a T1 document.
    Runs phased Gemini vision calls (identity, income, tax, preparer) after comparison/forensics.
    Use this when combined validation returns sparse T1 data.
    """,
)
async def extract_t1_document(
    file: UploadFile = File(..., description="T1 Income Tax Return (PDF)"),
):
    content = await _read_pdf(file)
    return _run_extraction(content, "t1")


@router.post(
    "/documents/extract/noa",
    response_model=DocumentExtractionResponse,
    summary="Deep extract Notice of Assessment fields",
    description="""
    Dedicated extraction pass for a NOA document.
    Runs phased Gemini vision calls (identity, amounts, credits).
    """,
)
async def extract_noa_document(
    file: UploadFile = File(..., description="Notice of Assessment (PDF)"),
):
    content = await _read_pdf(file)
    return _run_extraction(content, "noa")
