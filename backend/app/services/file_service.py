from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_DIR


def validate_extension(filename: str) -> None:
    file_extension = Path(filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed extensions: {allowed}",
        )


async def validate_file_size(upload_file: UploadFile) -> None:
    content = await upload_file.read()
    file_size_bytes = len(content)
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is too large. Maximum size is {MAX_FILE_SIZE_MB} MB.",
        )

    await upload_file.seek(0)


async def save_uploaded_file(upload_file: UploadFile) -> tuple[str, str]:
    filename = upload_file.filename or "uploaded_file"
    validate_extension(filename)
    await validate_file_size(upload_file)

    document_id = str(uuid4())
    uploads_path = Path(UPLOAD_DIR)
    uploads_path.mkdir(parents=True, exist_ok=True)

    saved_filename = f"{document_id}_{filename}"
    file_path = uploads_path / saved_filename

    file_content = await upload_file.read()
    file_path.write_bytes(file_content)
    await upload_file.seek(0)

    return document_id, str(file_path)
