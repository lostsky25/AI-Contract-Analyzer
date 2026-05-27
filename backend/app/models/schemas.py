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
    full_text: str
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
    document_id: str | None = None


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


class IndexRequest(BaseModel):
    document_id: str
    text: str


class IndexResponse(BaseModel):
    document_id: str
    status: str
    chunks_count: int


class RetrieveRequest(BaseModel):
    query: str
    document_id: str | None = None
    top_k: int = 5


class RetrieveResponse(BaseModel):
    status: str
    results: list[dict]


class OcrRequest(BaseModel):
    document_id: str
    file_path: str


class OcrResponse(BaseModel):
    document_id: str
    status: str
    text_preview: str
    text_length: int


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class OrchestrateRequest(BaseModel):
    document_id: str


class OrchestrateResponse(BaseModel):
    document_id: str
    status: str
    summary: str
    overall_risk: str
    risks: list[dict]
    key_terms: list[dict]
    disclaimer: str
    used_ocr: bool
    chunks_count: int
