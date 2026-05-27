from fastapi import APIRouter, File, UploadFile

from app.models.schemas import UploadResponse
from app.services.file_service import save_uploaded_file

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
