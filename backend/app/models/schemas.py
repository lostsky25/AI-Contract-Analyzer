from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    file_path: str


class ExtractRequest(BaseModel):
    document_id: str
    file_path: str


class ExtractResponse(BaseModel):
    document_id: str
    status: str
    text_preview: str
    text_length: int


class ProcessRequest(BaseModel):
    document_id: str
    file_path: str


class ProcessResponse(BaseModel):
    document_id: str
    status: str
    text_preview: str
    text_length: int
    used_ocr: bool
