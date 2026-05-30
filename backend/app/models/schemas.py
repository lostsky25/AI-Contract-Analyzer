from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SEVERITY_VALUES = {"low", "medium", "high", "unknown"}
SOURCE_TYPE_VALUES = {
    "consultant_plus",
    "garant",
    "pravo_gov",
    "other_public_source",
}
RELEVANCE_VALUES = {"low", "medium", "high", "unknown"}
STATUS_VALUES = {"processing", "done", "failed", "done_with_warnings"}
OVERALL_RISK_VALUES = {"low", "medium", "high", "unknown"}


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str


class ExtractRequest(BaseModel):
    document_id: str


class ExtractResponse(BaseModel):
    document_id: str
    status: str
    text_preview: str
    text_length: int


class ProcessRequest(BaseModel):
    document_id: str


class ProcessResponse(BaseModel):
    document_id: str
    status: str
    text_preview: str
    full_text: str
    text_length: int
    chunks_count: int
    used_ocr: bool
    warnings: list[str] = Field(default_factory=list)


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


class DocumentAnalyzeRequest(BaseModel):
    legal_web_search_enabled: bool = True


class OrchestrateRequest(BaseModel):
    document_id: str
    legal_web_search_enabled: bool = True


class OrchestrateResponse(BaseModel):
    document_id: str
    status: str
    summary: str
    overall_risk: str
    risks: list[dict]
    key_terms: list[dict]
    legal_sources: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str
    used_ocr: bool
    chunks_count: int


class ContractRisk(BaseModel):
    title: str
    severity: str = "unknown"
    explanation: str
    quote: str
    page: int | None = None

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, value: object) -> str:
        normalized = str(value or "unknown").strip().lower()
        return normalized if normalized in SEVERITY_VALUES else "unknown"


class ContractKeyTerm(BaseModel):
    title: str
    value: str
    quote: str
    page: int | None = None


class ContractLegalSource(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str = "other_public_source"
    relevance: str = "unknown"

    @field_validator("source_type", mode="before")
    @classmethod
    def normalize_source_type(cls, value: object) -> str:
        normalized = str(value or "other_public_source").strip().lower()
        return normalized if normalized in SOURCE_TYPE_VALUES else "other_public_source"

    @field_validator("relevance", mode="before")
    @classmethod
    def normalize_relevance(cls, value: object) -> str:
        normalized = str(value or "unknown").strip().lower()
        return normalized if normalized in RELEVANCE_VALUES else "unknown"


class ContractReport(BaseModel):
    document_id: str
    status: str = "done"
    summary: str = ""
    overall_risk: str = "unknown"
    risks: list[ContractRisk] = Field(default_factory=list)
    key_terms: list[ContractKeyTerm] = Field(default_factory=list)
    legal_sources: list[ContractLegalSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str
    used_ocr: bool = False
    chunks_count: int = 0

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> str:
        normalized = str(value or "done").strip().lower()
        return normalized if normalized in STATUS_VALUES else "done"

    @field_validator("overall_risk", mode="before")
    @classmethod
    def normalize_overall_risk(cls, value: object) -> str:
        normalized = str(value or "unknown").strip().lower()
        return normalized if normalized in OVERALL_RISK_VALUES else "unknown"


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str


class DocumentAskRequest(BaseModel):
    question: str


class DocumentAskCitation(BaseModel):
    quote: str
    page: int | None = None
    chunk_id: str = ""


class DocumentAskResponse(BaseModel):
    document_id: str
    question: str
    answer: str
    confidence: str
    citations: list[DocumentAskCitation]
    disclaimer: str


class ProviderErrorResponse(BaseModel):
    detail: str
    code: str
    provider: str
    retryable: bool

