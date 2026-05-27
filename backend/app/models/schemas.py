from datetime import datetime

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
    chunks_count: int
    used_ocr: bool


class ChunkRequest(BaseModel):
    text: str
    chunk_size: int = 1200
    overlap: int = 200


class ChunkResponse(BaseModel):
    status: str
    chunks_count: int
    chunks: list[str]


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    status: str
    summary: str
    risks: list[dict]


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    file_path: str
    status: str
    text_length: int | None
    created_at: datetime
