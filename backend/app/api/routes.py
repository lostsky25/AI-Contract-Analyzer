from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import ExtractRequest, ExtractResponse, UploadResponse
from app.services.file_service import save_uploaded_file
from app.services.text_extractor import extract_text

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    document_id, saved_path = await save_uploaded_file(file)
    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "uploaded_file",
        status="uploaded",
        file_path=saved_path,
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract_document_text(payload: ExtractRequest) -> ExtractResponse:
    target_file = Path(payload.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        extracted_text = extract_text(payload.file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract text from document.",
        ) from exc

    text_length = len(extracted_text)
    status_value = "extracted" if text_length > 0 else "empty_text"

    return ExtractResponse(
        document_id=payload.document_id,
        status=status_value,
        text_preview=extracted_text[:1000],
        text_length=text_length,
    )
